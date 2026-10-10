'use client';

import {useSyncExternalStore} from 'react';

const subscribe = () => () => {};
const client = () => true;
const server = () => false;

/** Keep server-rendered controls disabled until their event handlers exist. */
export function useReady() {
  return useSyncExternalStore(subscribe, client, server);
}
