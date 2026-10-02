-- INUKO LAB Portfolio Cloud v1
-- Safe to commit: schema only. Never place a Supabase service-role key in this repo.

create extension if not exists pgcrypto;

create or replace function public.inuko_set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.inuko_brokerage_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 40),
  account_kind text not null default 'custom' check (account_kind in ('main','secondary','custom')),
  currency text not null default 'TWD' check (currency = 'TWD'),
  sort_order integer not null default 100,
  archived_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (user_id, name),
  unique (id, user_id)
);

create table if not exists public.inuko_portfolio_ledgers (
  account_id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  schema_version text not null default '2.0.0',
  revision bigint not null default 0 check (revision >= 0),
  ledger jsonb not null default '{"schema_version":"2.0.0","transactions":[],"meta":{}}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint inuko_ledger_account_owner_fk
    foreign key (account_id, user_id)
    references public.inuko_brokerage_accounts(id, user_id)
    on delete cascade,
  constraint inuko_ledger_json_object check (jsonb_typeof(ledger) = 'object')
);

create table if not exists public.inuko_fee_profiles (
  account_id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  commission_rate numeric(12,8),
  minimum_commission_twd numeric(12,2),
  odd_lot_minimum_commission_twd numeric(12,2),
  sell_tax_rate numeric(12,8),
  daytrade_sell_tax_rate numeric(12,8),
  note text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint inuko_fee_account_owner_fk
    foreign key (account_id, user_id)
    references public.inuko_brokerage_accounts(id, user_id)
    on delete cascade
);

create table if not exists public.inuko_portfolio_snapshots (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  snapshot_date date not null,
  schema_version text not null default '2.0.0',
  ledger jsonb not null,
  source_revision bigint not null default 0,
  created_at timestamptz not null default timezone('utc', now()),
  constraint inuko_snapshot_account_owner_fk
    foreign key (account_id, user_id)
    references public.inuko_brokerage_accounts(id, user_id)
    on delete cascade,
  constraint inuko_snapshot_json_object check (jsonb_typeof(ledger) = 'object'),
  unique (account_id, snapshot_date)
);

create index if not exists inuko_accounts_user_idx on public.inuko_brokerage_accounts(user_id, archived_at, sort_order);
create index if not exists inuko_snapshots_user_account_date_idx on public.inuko_portfolio_snapshots(user_id, account_id, snapshot_date desc);

create trigger inuko_accounts_set_updated_at
before update on public.inuko_brokerage_accounts
for each row execute function public.inuko_set_updated_at();

create trigger inuko_ledgers_set_updated_at
before update on public.inuko_portfolio_ledgers
for each row execute function public.inuko_set_updated_at();

create trigger inuko_fee_profiles_set_updated_at
before update on public.inuko_fee_profiles
for each row execute function public.inuko_set_updated_at();

alter table public.inuko_brokerage_accounts enable row level security;
alter table public.inuko_portfolio_ledgers enable row level security;
alter table public.inuko_fee_profiles enable row level security;
alter table public.inuko_portfolio_snapshots enable row level security;

create policy "inuko_accounts_select_own" on public.inuko_brokerage_accounts
for select to authenticated using (auth.uid() = user_id);
create policy "inuko_accounts_insert_own" on public.inuko_brokerage_accounts
for insert to authenticated with check (auth.uid() = user_id);
create policy "inuko_accounts_update_own" on public.inuko_brokerage_accounts
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "inuko_accounts_delete_own" on public.inuko_brokerage_accounts
for delete to authenticated using (auth.uid() = user_id);

create policy "inuko_ledgers_select_own" on public.inuko_portfolio_ledgers
for select to authenticated using (auth.uid() = user_id);
create policy "inuko_ledgers_insert_own" on public.inuko_portfolio_ledgers
for insert to authenticated with check (auth.uid() = user_id);
create policy "inuko_ledgers_update_own" on public.inuko_portfolio_ledgers
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "inuko_ledgers_delete_own" on public.inuko_portfolio_ledgers
for delete to authenticated using (auth.uid() = user_id);

create policy "inuko_fee_select_own" on public.inuko_fee_profiles
for select to authenticated using (auth.uid() = user_id);
create policy "inuko_fee_insert_own" on public.inuko_fee_profiles
for insert to authenticated with check (auth.uid() = user_id);
create policy "inuko_fee_update_own" on public.inuko_fee_profiles
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "inuko_fee_delete_own" on public.inuko_fee_profiles
for delete to authenticated using (auth.uid() = user_id);

create policy "inuko_snapshots_select_own" on public.inuko_portfolio_snapshots
for select to authenticated using (auth.uid() = user_id);
create policy "inuko_snapshots_insert_own" on public.inuko_portfolio_snapshots
for insert to authenticated with check (auth.uid() = user_id);
create policy "inuko_snapshots_update_own" on public.inuko_portfolio_snapshots
for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "inuko_snapshots_delete_own" on public.inuko_portfolio_snapshots
for delete to authenticated using (auth.uid() = user_id);

-- Creates the two default accounts only when a signed-in user has none yet.
create or replace function public.inuko_ensure_default_accounts()
returns setof public.inuko_brokerage_accounts
language plpgsql
security definer
set search_path = public
as $$
declare
  uid uuid := auth.uid();
begin
  if uid is null then
    raise exception 'authentication required';
  end if;

  if not exists (
    select 1 from public.inuko_brokerage_accounts
    where user_id = uid and archived_at is null
  ) then
    insert into public.inuko_brokerage_accounts(user_id, name, account_kind, sort_order)
    values
      (uid, '主帳戶', 'main', 10),
      (uid, '第二帳戶', 'secondary', 20);
  end if;

  insert into public.inuko_portfolio_ledgers(account_id, user_id)
  select a.id, a.user_id
  from public.inuko_brokerage_accounts a
  where a.user_id = uid and a.archived_at is null
  on conflict (account_id) do nothing;

  insert into public.inuko_fee_profiles(account_id, user_id)
  select a.id, a.user_id
  from public.inuko_brokerage_accounts a
  where a.user_id = uid and a.archived_at is null
  on conflict (account_id) do nothing;

  return query
  select * from public.inuko_brokerage_accounts
  where user_id = uid and archived_at is null
  order by sort_order, created_at;
end;
$$;

revoke all on function public.inuko_ensure_default_accounts() from public;
grant execute on function public.inuko_ensure_default_accounts() to authenticated;
