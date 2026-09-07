/* Static data adapter for GitHub Pages, including /repository/ base paths. */
(function(){
  'use strict';
  const config=window.SMALLCAP_CONFIG||{};if(config.mode!=='github')return;
  const cache=new Map();let revision='';
  async function json(path,refresh=false){if(refresh)cache.delete(path);if(!cache.has(path))cache.set(path,fetch(new URL(path,document.baseURI),{cache:'no-cache'}).then(async r=>{if(!r.ok)throw Error('The saved data file is unavailable. Try refreshing the page.');return r.json();}).catch(e=>{cache.delete(path);throw e;}));return cache.get(path);}
  window.SmallcapStatic={
    async request(url,options={}){
      const u=new URL(url,location.origin),parts=u.pathname.split('/').filter(Boolean);
      if(options.method&&options.method!=='GET')throw Error('Hosted data is updated by the daily GitHub workflow. Use its Run workflow button for an extra update.');
      if(u.pathname==='/api/status'){const s=await json('data/status.json',true);if(revision&&revision!==s.server_time){cache.clear();cache.set('data/status.json',Promise.resolve(s));}revision=s.server_time;return s;}
      if(u.pathname==='/api/funds')return json('data/funds.json');
      if(parts[1]==='funds'){
        const f=await json('data/funds/'+Number(parts[2])+'.json');
        if(parts[3]==='documents')return json('data/communications/'+f.family_id+'.json');
        if(parts[3]==='performance'){const [nav,benchmarks]=await Promise.all([json('data/nav/'+f.code+'.json'),json('data/benchmarks.json')]);const q=Object.fromEntries(u.searchParams);return window.SmallcapAnalytics.response(f,nav,benchmarks[q.benchmark],q);}
        return f;
      }
      if(parts[1]==='portfolios')return json('data/portfolios/'+Number(parts[2])+'.json');
      throw Error('This operation is available in the local edition.');
    },
    async download(path){const map=await json('data/downloads.json');return map[path]?new URL(map[path],document.baseURI).href:null;}
  };
  document.addEventListener('click',async e=>{const a=e.target.closest('a[href]');if(!a)return;const u=new URL(a.href);if(!u.pathname.startsWith('/api/'))return;e.preventDefault();
    const target=await window.SmallcapStatic.download(u.pathname);if(target){const link=document.createElement('a');link.href=target;link.download='';link.rel='noopener';document.body.append(link);link.click();link.remove();}
    else if(u.pathname==='/api/export/backup'&&config.repository)window.open('https://github.com/'+config.repository+'/releases/tag/tracker-history','_blank','noopener');
    else if(typeof toast==='function')toast('Open the original source link or download the full archive from the project release.');
  });
})();
