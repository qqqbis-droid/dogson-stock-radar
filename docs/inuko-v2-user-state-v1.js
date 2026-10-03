(()=>{
'use strict';
// Emergency rollback: temporarily disable the V2 favorites/autosave helper.
// The Supabase user-state table and any saved local data are intentionally preserved.
window.__INUKO_V2_USER_STATE_V1__=true;
})();
