import {test,expect,type Page} from '@playwright/test';

type Message={role:'user'|'assistant';content:string;evidence_ids:string[];message_id:string;created_at:string;status:'VALID'};
type Conversation={thread_id:string;fund_code:string;scope:string;title:string;items:Message[]};

async function storedChat(page:Page){
  let scope='live',counter=0,calls=0;const conversations:Conversation[]=[];
  await page.route('**/api/p/chat/threads?**',route=>{
    const fund=new URL(route.request().url()).searchParams.get('fund_code');
    return route.fulfill({json:{fund_code:fund,analysis_scope_key:scope,items:conversations.filter(item=>item.fund_code===fund&&item.scope===scope).slice().reverse().map(item=>({thread_id:item.thread_id,title:item.title,created_at:'2026-10-10T12:00:00Z',last_message_at:'2026-10-10T12:00:01Z',message_count:item.items.length}))}});
  });
  await page.route(/\/api\/p\/chat\/[a-f0-9-]{36}\?/,route=>{
    const url=new URL(route.request().url()),id=url.pathname.split('/').at(-1),fund=url.searchParams.get('fund_code');
    const item=conversations.find(item=>item.thread_id===id&&item.fund_code===fund&&item.scope===scope);
    return item?route.fulfill({json:{thread_id:id,fund_code:fund,analysis_scope_key:scope,items:item.items}}):route.fulfill({status:404,json:{detail:'THREAD_NOT_FOUND'}});
  });
  await page.route('**/api/p/chat',route=>{
    calls++;const body=route.request().postDataJSON();
    let item=conversations.find(item=>item.thread_id===body.thread_id&&item.scope===scope&&item.fund_code===body.fund_code);
    if(!item){item={thread_id:`00000000-0000-4000-8000-${String(++counter).padStart(12,'0')}`,fund_code:body.fund_code,scope,title:body.question,items:[]};conversations.push(item);}
    const content=`Kayıtlı yanıt: ${body.question}`;
    item.items.push({role:'user',content:body.question,evidence_ids:[],message_id:String(item.items.length+1),created_at:'2026-10-10T12:00:00Z',status:'VALID'},
      {role:'assistant',content,evidence_ids:['ev:synthetic-history'],message_id:String(item.items.length+2),created_at:'2026-10-10T12:00:01Z',status:'VALID'});
    return route.fulfill({contentType:'text/event-stream',body:`event: thread\ndata: ${JSON.stringify({thread_id:item.thread_id,analysis_scope_key:scope})}\n\nevent: answer\ndata: ${JSON.stringify({thread_id:item.thread_id,content,evidence_ids:['ev:synthetic-history'],model:'synthetic-browser-model'})}\n\n`});
  });
  return {setScope:(value:string)=>{scope=value;},calls:()=>calls};
}
async function login(page:Page){
  await page.goto('/login');await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');
  await page.getByLabel('Parola',{exact:true}).fill('synthetic-browser-password');
  await page.getByRole('button',{name:'Giriş yap',exact:true}).click();await expect(page).toHaveURL(/\/funds$/);
}
async function open(page:Page){
  await page.getByRole('button',{name:'Kanıtlarla sohbet',exact:true}).click();
  await expect(page.getByLabel('Fon kanıtları hakkında sorunuz')).toBeEnabled();
}

test('asset chat restores server history after navigation and reload and can select older conversations',async({page})=>{
  await storedChat(page);await login(page);await page.goto('/funds/THF');await open(page);
  const input=page.getByLabel('Fon kanıtları hakkında sorunuz');
  await input.fill('Kaynakları açıkla');await input.press('Enter');
  await expect(page.locator('.chat-assistant')).toHaveText(/Kayıtlı yanıt: Kaynakları açıkla/);
  await page.goto('/funds');await page.goto('/funds/THF');await open(page);
  await expect(page.locator('.chat-assistant')).toHaveText(/Kayıtlı yanıt: Kaynakları açıkla/);
  await page.evaluate(()=>localStorage.clear());await page.reload();await open(page);
  await expect(page.locator('.chat-assistant')).toHaveText(/Kayıtlı yanıt: Kaynakları açıkla/);
  await page.getByRole('button',{name:'Yeni sohbet',exact:true}).click();
  await input.fill('Eksik bilgiyi açıkla');await input.press('Enter');
  await expect(page.locator('.chat-assistant')).toHaveText(/Kayıtlı yanıt: Eksik bilgiyi açıkla/);
  await page.getByLabel('Kayıtlı sohbet').selectOption('00000000-0000-4000-8000-000000000001');
  await expect(page.locator('.chat-assistant')).toHaveText(/Kayıtlı yanıt: Kaynakları açıkla/);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});

test('Enter sends while Shift+Enter and IME composition preserve the draft',async({page})=>{
  const store=await storedChat(page);await login(page);await page.goto('/funds/THF');await open(page);
  const input=page.getByLabel('Fon kanıtları hakkında sorunuz');
  await input.fill('Kaynaklar');await input.press('Shift+Enter');await expect(input).toHaveValue('Kaynaklar\n');
  await input.dispatchEvent('compositionstart');
  await input.dispatchEvent('keydown',{key:'Enter',code:'Enter',keyCode:229,isComposing:true,bubbles:true});
  expect(store.calls()).toBe(0);
  await input.dispatchEvent('compositionend');await input.press('Enter');
  await expect(page.locator('.chat-assistant')).toBeVisible();expect(store.calls()).toBe(1);
});

test('changing the analysis date never restores the live transcript into a historical view',async({page,context})=>{
  const store=await storedChat(page);await login(page);await page.goto('/funds/THF');await open(page);
  await page.getByLabel('Fon kanıtları hakkında sorunuz').fill('Güncel kaynağı açıkla');await page.keyboard.press('Enter');
  await expect(page.locator('.chat-assistant')).toContainText('Kayıtlı yanıt: Güncel kaynağı açıkla');
  store.setScope('asof:2026-09-12');await context.addCookies([{name:'p50k_as_of',value:'2026-09-12',url:'http://127.0.0.1:3071'}]);
  await page.reload();await open(page);
  await expect(page.locator('.chat-assistant')).toHaveCount(0);
  await expect(page.locator('.chat-scope-label')).toContainText('12 Eyl 2026');
  store.setScope('live');await context.addCookies([{name:'p50k_as_of',value:'live',url:'http://127.0.0.1:3071'}]);
  await page.reload();await open(page);
  await expect(page.locator('.chat-assistant')).toContainText('Kayıtlı yanıt: Güncel kaynağı açıkla');
});
