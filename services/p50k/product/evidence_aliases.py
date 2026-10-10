"""Short model-local evidence references, resolved back to immutable IDs by the server."""
from __future__ import annotations
from p50k.product.egress import Packet
from p50k.product.validator import PLACEHOLDER


def references(packet: Packet) -> dict[str,str]:
    return {f'e{index+1}':item.evidence_id for index,item in enumerate(packet.evidence)}


def model_packet(packet: Packet) -> Packet:
    inverse={value:key for key,value in references(packet).items()}
    return packet.model_copy(update={'evidence':[item.model_copy(update={'evidence_id':inverse[item.evidence_id]}) for item in packet.evidence]})


def resolve_text(text: str, packet: Packet) -> str:
    aliases=references(packet)
    def replace(match):
        key=match.group(1)
        return '{{ev:'+aliases[key]+'}}' if key in aliases else match.group(0)
    return PLACEHOLDER.sub(replace,text)


def resolve_ids(ids: list[str], packet: Packet) -> list[str]:
    aliases=references(packet)
    return [aliases.get(key,key) for key in ids]
