"""Short model-local evidence references, resolved back to immutable IDs by the server."""
from __future__ import annotations
import re
from p50k.product.egress import Packet
from p50k.product.validator import PLACEHOLDER


def references(packet: Packet) -> dict[str,str]:
    return {f'e{index+1}':item.evidence_id for index,item in enumerate(packet.evidence)}


def model_packet(packet: Packet, *, anonymous: bool=False) -> Packet:
    inverse={value:key for key,value in references(packet).items()}
    update={'evidence':[item.model_copy(update={'evidence_id':inverse[item.evidence_id]}) for item in packet.evidence]}
    if anonymous:update.update(fund_code='FUND',fund_name='İncelenen fon')
    return packet.model_copy(update=update)


def blind_question(text: str, packet: Packet) -> str:
    """Remove the selected instrument's names from historical model questions."""
    manager=re.split(r'\s+PORTF[ÖO]Y\b',packet.fund_name,flags=re.I)[0]
    names=[packet.fund_name,packet.fund_code]
    if len(manager)>2 and manager!=packet.fund_name:names.append(manager)
    for name in sorted(names,key=len,reverse=True):
        text=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)','bu fon',text,flags=re.I)
    return text


def resolve_text(text: str, packet: Packet) -> str:
    aliases=references(packet)
    def replace(match):
        key=match.group(1)
        return '{{ev:'+aliases[key]+'}}' if key in aliases else match.group(0)
    return PLACEHOLDER.sub(replace,text)


def resolve_ids(ids: list[str], packet: Packet) -> list[str]:
    aliases=references(packet)
    return [aliases.get(key,key) for key in ids]
