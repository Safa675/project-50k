// Placeholder mascot art for the Raportör (DEC-035 allows it until Barış or Mirza supply the design).
// Keep it self-contained so the final artwork can replace this file without touching the dock.
export default function Mascot({size = 40, className}: {size?: number; className?: string}) {
  return <svg className={`ag-mascot${className ? ` ${className}` : ''}`} viewBox="0 0 48 48" width={size} height={size} aria-hidden="true" focusable="false">
    <g transform="translate(1.4 1.2)">
      <path className="ag-mascot-body" d="M11.4 31.6c0-3 2.7-4.8 6.4-4.5l6.1.5c3.3.3 5.9-.6 8.3-2.7l2.6-2.3c.8-.7 2.1 0 1.9 1.1l-.3 1.7 1.3-.8c.9-.5 2 .3 1.7 1.3-1.7 5.8-6.9 10.4-14 10.4h-7.6c-3.8 0-6.4-2.1-6.4-4.7Z"/>
      <path className="ag-mascot-neck" d="M15.4 28.8c4.3-2.9 6.3-8 4.1-12.6-1-2.1-2-3.6-1.8-5" fill="none" strokeWidth="3.6" strokeLinecap="round"/>
      <circle className="ag-mascot-body" cx="16.6" cy="10.6" r="3"/>
      <path className="ag-mascot-beak" d="M14.2 9.6 10.2 12.9l4.9-.9Z" strokeWidth=".9" strokeLinejoin="round"/>
      <circle className="ag-mascot-eye" cx="16.5" cy="9.9" r=".85"/>
      <path className="ag-mascot-wing" d="M21.8 31.4c3.3 1.4 7.6 1.1 10.6-1" fill="none" strokeWidth="1.3" strokeLinecap="round"/>
    </g>
  </svg>;
}
