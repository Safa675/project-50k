'use client';

import {useEffect, useState} from 'react';
import {AgentPageContext, type AgentPageInfo, useAgentPage} from './hooks';

/** Wraps the app shell so a page can tell the Raportör which fund (and evidence) it shows. */
export function AgentPageProvider({children}: {children: React.ReactNode}) {
  const [page, setPage] = useState<AgentPageInfo | null>(null);
  return <AgentPageContext.Provider value={{page, setPage}}>{children}</AgentPageContext.Provider>;
}

/** Rendered by a page that is about one fund; the dock then opens that fund's conversation. */
export default function AgentPage({fundCode, evidenceId, title}: {fundCode: string | null; evidenceId?: string; title?: string}) {
  const {setPage} = useAgentPage();
  useEffect(() => {
    setPage({fundCode, evidenceId, title});
    return () => setPage(null);
  }, [fundCode, evidenceId, title, setPage]);
  return null;
}
