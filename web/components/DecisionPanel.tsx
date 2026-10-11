'use client';
import ReviewActions from './review/ReviewActions';
import {EvidenceLinks,Rationale,toneClass} from './review/ReviewCard';
import {decisionLabel,decisionTone,proposalOriginLabel,proposalSource,reviewStateLabel,reviewedAtTr,type Decision} from './review/review-logic';
import styles from './review/review.module.css';
import {friendlyEvidenceText} from '@/lib/fund-display';
export type {Decision} from './review/review-logic';

function decidedByText(decision:Decision):string{
  if(decision.decided_by==='HUMAN')return 'Etkin karar insan incelemesine dayanıyor.';
  if(proposalSource(decision)==='rules')return 'Sabit hesaplamalardan gelen sonuç; son karar insan incelemesiyle kaydedilir.';
  if(proposalSource(decision)==='synthetic')return 'Örnek test verisiyle üretilen öneri.';
  if(decision.decided_by==='AI')return decision.team_proposal?'Ajan ekibinin Raportör önerisi; insan tarafından değiştirilebilir.':'Yapay zekâ önerisi; insan tarafından değiştirilebilir.';
  return 'Bu konu için henüz bir değerlendirme bulunmuyor.';
}

/** The effective decision of one fund with its evidence, the human review record and, for analysts, the review actions. */
export default function DecisionPanel({decision,canReview}:{decision:Decision;canReview:boolean}){
  return <div className={styles.panel}>
    <div className={styles.proposalLine}><p className={styles.source}>{proposalOriginLabel(decision)}</p><span className={styles.reviewState}>{reviewStateLabel(decision)}</span></div>
    <div className={styles.panelHead}>
      <h3 className={`${toneClass[decisionTone(decision.effective_value)]} ${styles.panelTitle}`}>{decisionLabel(decision.effective_value)}</h3>
      <p className={styles.panelMeta}>{decidedByText(decision)}</p>
    </div>
    <Rationale text={friendlyEvidenceText(decision.rationale_tr)}/>
    {decision.decided_by==='HUMAN'&&<dl className={styles.record}>
      <div><dt>İlk öneri (korunur)</dt><dd>{decisionLabel(decision.original_value)}</dd></div>
      <div><dt>İnceleyen</dt><dd>{decision.reviewer_email??'Kayıtlı değil'} · {reviewedAtTr(decision.reviewed_at)}</dd></div>
      <div><dt>İnceleme gerekçesi</dt><dd>{decision.review_reason??'Öneri kabul edildi'}</dd></div>
    </dl>}
    {decision.stale_review_exists&&!decision.has_current_review&&<p className={styles.stale}>Önceki insan kararı farklı kanıta aittir. Yeni inceleme gerekir.</p>}
    <EvidenceLinks decision={decision}/>
    {canReview&&decision.decision_id!==null&&<div className={styles.panelActions}><ReviewActions decision={decision}/></div>}
  </div>;
}
