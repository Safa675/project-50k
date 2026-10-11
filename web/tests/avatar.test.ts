import {describe,expect,it} from 'vitest';
import {accountInitials,avatarSource} from '../lib/avatar';

describe('header avatar',()=>{
  it('accepts only same-origin photo paths under /avatars/',()=>{
    for(const path of ['/avatars/synthetic.jpg','/avatars/a.png','/avatars/team-1.webp',`/avatars/${'a'.repeat(40)}.jpg`])expect(avatarSource(path)).toBe(path);
    for(const path of [null,undefined,42,'','https://example.invalid/avatars/a.jpg','//example.invalid/avatars/a.jpg','/avatars/../a.jpg','/avatars/A.jpg','/avatars/-a.jpg','/avatars/a.gif','/avatars/a.jpg?x=1','/avatars/a.jpg\n','/avatars/sub/a.jpg','/design/a.jpg','javascript:alert(1)',`/avatars/${'a'.repeat(41)}.jpg`])expect(avatarSource(path)).toBeNull();
  });
  it('falls back to Turkish upper-case initials',()=>{
    expect(accountInitials('synthetic@example.invalid')).toBe('SY');
    expect(accountInitials('ilker@example.invalid')).toBe('İL');
  });
});
