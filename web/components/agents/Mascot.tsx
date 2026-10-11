/** The supplied BlackSwan Raportor artwork, shared by the dock and conversation. */
export default function Mascot({size = 40, className}: {size?: number; className?: string}) {
  return <img className={`ag-mascot${className ? ` ${className}` : ''}`} src="/agent-logos/blackswan-raportor.svg"
    width={size} height={size} alt="" aria-hidden="true" draggable={false}/>;
}
