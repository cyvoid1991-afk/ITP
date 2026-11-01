# Root Delegation & Intent Delta Procedure — v0.3

이 문서는 [Root 공통 instruction v0.3](Root_Autonomy_Instruction_v0.3.md)의 두 workflow 운용 절차다. A는 `intent-realization`, B는 `build-tool-pipeline`의 기존 skill·agent·실행 제어를 사용한다. 상태 명령은 해당 gate-map을 따른다. 자연어 의미 판단을 자동화한 별도 agent나 harness가 아니다.

## 1. Workflow A에서 intent와 위임 경계를 준비한다

사용자는 외부 ChatGPT 등에서 목적·사용경험·중요한 선택을 충분히 토론하고 수렴한 intent를 Root에게 제공한다. 이 상호작용 자체를 없애는 것이 목표가 아니다. Root는 제공된 원문·명시적 결정·관련 제품 근거를 읽고, 외부 대화를 보지 않아도 이해할 수 있도록 출처와 실제 내용을 보존한다. 필요한 사용자 정보가 빠졌으면 그 정보만 확인한다.

Root는 명시적 위임·제한 중심의 최소 skeleton을 기존 기록에 정리한다. 별도 skeleton 파일이나 일괄 승인 gate는 만들지 않는다. Realizer가 의미·실현 조건·근거·가정·준비도를 작성하고, Root는 조사·probe·기존 결정 전달과 사용자 확인을 지휘한다. Realizer가 필요한 조건을 제안하는 것과 사용자 손실·선호를 결정하거나 Root 권한을 승인하는 것은 다르다.

Root가 [작업별 위임 양식](Task_Delegation_Contract_Template_v0.3.md)을 이용해 기존 권한의 적용 경계를 정리한다. 제품 요구사항을 중복 작성하지 말고 보존조건과 재량·유보 영역만 원문 참조와 함께 추린다. 나머지는 공통 instruction을 상속한다. 중요한 기술 대안도 기존 위임과 근거로 해결되면 Root가 결정한다.

사용자에게 전체 위임표의 작성을 요구하거나 모든 항목의 일괄 승인을 요청하지 않는다. 기존 위임을 확장하는 항목이나 사용자만 정할 중요한 미결정만 분리하여 확인한다. 그런 항목은 승인 전까지 채택하지 않되, 영향을 받지 않는 작업은 기존 gate 범위에서 계속한다.

인계 전 Realizer의 준비도를 확인하고, 원문·사용자 결정, 담당이 반환한 complete brief, 위임 경계, 미결정·제한·증거·재검토 조건의 적용 버전을 기존 기록의 짧은 인덱스로 묶는다. run의 `source_context`, brief의 `Input Reviewed`/`Decisions`/`Handoff Readiness`와 기존 실행 기록을 재사용한다. 원문 snapshot과 위임 기록은 해당 run의 `00_intake/`에 두고 참조할 수 있다. 동일 요구사항을 새 통합 문서에 반복하지 않는다. downstream이 원문 대화 없이 읽을 수 있어야 한다.

중요한 의미를 새로 추측하지 않고 계약을 작성할 수 있으면 A의 인계가 가능하다. 비차단 가정과 위임된 구현 선택은 남길 수 있다. Root는 담당이 채택한 bytes와 참조를 고정·저장할 뿐 의미를 재작성하거나 자신의 권한을 승인하지 않는다. Realizer readiness는 Contractor의 실제 intake 판단을 대체하지 않는다.

저장 후의 실제 해시는 `active_artifacts` 또는 별도 기존 인계 인덱스에 남긴다. brief나 위임 기록 내부에 자기 자신의 최종 해시를 넣도록 요구하지 않고, 이를 채우려고 담당 반환문을 Root가 수정하지 않는다.

## 2. Workflow B의 첫 intake와 재개

준비된 경로는 Root + Contractor가 인계본을 받아 시작한다. Root는 원문·brief·위임·관련 증거의 위치와 버전/해시, 담당 반환과 저장본의 일치, 미결정과 보류 범위를 확인한다. Contractor는 원문을 직접 비교하여 실제 계약 작성 가능성과 제안된 조건의 필요성을 판정한다. 이미 준비된 brief나 위임표를 처음부터 다시 만들지 않는다.

간단하고 명확한 직접 요청은 Root + Contractor로 진입한다. 목적·범위·중요한 의미와 제약이 명확하고 Contractor가 acceptance를 형식화할 수 있어야 한다. 기존 intake의 rationale에 직접 진입 근거를 남기고, 필요한 작업별 차이·유보·미결정만 기존 decisions/assumptions/blockers에 기록한다. A·전체 위임 양식·가상의 Realizer 산출물을 강제하지 않는다. 계약·테스트·독립 검증·repair·release 조건은 그대로다.

중단 후 재개·맥락 축약 후 복구 시에는 기억이나 요약문만으로 이어가지 말고, 인계 또는 직접 요청의 기준본, 현재 적용 버전, 미결정 사항과 관련 판정을 다시 확인한다. 사용자 결정으로 기준이 바뀌면 변경 이력을 유지한다. 최신 제품 계약을 채택했다는 이유만으로 출발점의 intent와 비교할 근거를 없애지 않는다.

각 agent에게는 담당 작업에 필요한 원문·보존조건·Root 결정과 미결정 상태를 함께 전달한다. Root의 해석 요약만 전달하지 않는다. Root의 역할 instruction 전체를 다른 agent에 주입하여 그 agent의 책임을 바꾸지는 않는다.

## 3. B의 Bounce-back과 A로의 제한적 반환

| 확인 결과 | Root의 조치 | 확정·판정 책임 |
| --- | --- | --- |
| 기존 근거를 전달하면 해결되는 맥락 누락 | 원문·관련 결정·증거를 찾아 전달한다. | 반환한 agent가 산출물과 준비도를 갱신한다. |
| 조사·분석·실험으로 판단 가능한 기술 문제 | 필요한 근거를 확보하고 위임 범위 안의 해결안을 결정한다. | brief·계약 변경은 각각 Realizer·Contractor, 기술 판정은 Verifier가 맡는다. |
| 기존 intent에 비추어 잘못 작성된 brief·계약 | 잘못된 표현과 원문 근거를 특정하여 수정 요청한다. | 해당 작성 agent가 수정·재판정한다. 사용자 질문은 자동으로 발생하지 않는다. |
| 위임되지 않은 중요한 의미·우선순위·손실·범위·추가 권한 선택 | 영향받는 확정을 보류하고 해당 쟁점만 A/사용자에게 반환한다. 미결정, 기존 근거, 권고안, 현실적 대안의 결과 차이를 함께 전달한다. | 사용자 결정 후 Realizer가 필요한 brief 부분, Contractor가 계약을 갱신한다. Root는 위임 근거와 인계 버전을 갱신한다. |
| 유용한 다음 접근이 없거나 자원·권한 한계 | 영향 작업을 보류하고 현재 한계를 보고한다. | 사용자에게 기술적 해답을 요구하지 않는다. 기존 운영 규칙을 따른다. |

분류의 근거는 작업 명칭이 아니라 결과 차이와 결정 권한이다. 구현에 관한 선택도 제품 의미를 바꾸면 중요할 수 있고, 중요한 기술 선택도 이미 위임된 범위라면 사용자에게 돌려보낼 필요가 없다.

맥락·기술·계약 표현 문제는 가능한 한 B에서 해결한다. Realizer의 brief 정정이 필요하면 담당에게 해당 부분을 반환하되 A 전체를 재시작하지 않는다. 직접 진입도 이후 중요한 미위임 의미가 드러나면 그 부분만 A/사용자에게 보낸다. 답변 전에는 독립 작업만 기존 권한과 gate 안에서 계속한다.

A에서 바뀐 합의는 원래 intent와 함께 보존하고 변경 이유·범위·위임·버전을 B에 전달한다. Contractor의 계약 재판정, 영향받는 구현·테스트, Verifier의 재검증을 연결한다. 전 단계의 PASS를 영향 분석 없이 유지하지 않는다. 반환 경로가 공식 repair 집계를 초기화하지 않는다.

## 4. 중요도와 권한을 별도로 확인한다

다음 세 가지를 짧게 구별한다.

1. **영향:** 대안이 결과 해석, 핵심 사용, 실패 처리, 품질, 수용, 비용·호환성·외부 영향에 실질적으로 다른 결과를 만드는가? 관련된 드문 사용조건과 다른 변경의 누적 영향도 포함한다.
2. **권한:** 이 차이를 선택할 재량이 기존 intent와 위임 범위에 있는가? 없다면 근거 조사로 해결할 사실 문제인가, 사용자만 정할 우선순위인가?
3. **채택 조건:** 어떤 근거와 담당 agent의 검토·검증을 거쳐야 실제 적용할 수 있는가?

선택의 중요도는 검토 강도를 정하고, 위임 여부는 사용자에게 결정 요청할지를 정한다. 중요한 영향이 있는지 확인하지 못했다는 이유로 경미하다고 분류하지 않는다. 그렇다고 모든 불확실성을 사용자에게 넘기지는 않는다. 먼저 영향 범위를 조사하고, 해소되지 않은 중요한 선택만 남긴다.

예를 들어 이미 정한 오차·자원 한도를 모두 충족하는 알고리즘 사이의 선택은 Root가 할 수 있다. 반면 실험에서 관찰한 오차만으로 사용자가 허용할 오차를 새로 정할 수는 없다. 기술적 달성 가능성의 증거와 손실을 수용할 권한은 다르다.

## 5. Intent Delta Check를 수행한다

Intent Delta Check는 의도 대비 변경·추가·누락·재해석을 확인하는 검토이며, 자동적인 의미 일치 증명은 아니다.

### 수행 시점

- A 인계 전과 B intake에서 원문·담당 brief·위임·미결정 사이의 일치를 확인한다. 직접 진입은 원문과 필요한 작업별 경계를 기준으로 한다.
- 최초 제품 계약의 준비도 판단 전, 인계 또는 직접 요청의 보존조건이 반영됐는지 확인한다.
- 중요한 결정이나 의미에 영향을 줄 수 있는 수정은 후속 단계의 확정 전 확인한다. 채택 뒤에는 실제 산출물·결과가 검토한 내용과 일치하는지 확인한다.
- 관련 intent·적용 범위·기술 가정이 바뀌면 영향을 받는 위임 판단부터 다시 확인한다.
- 최종 전달 전에는 개별 수정뿐 아니라 누적 결과를 확인한다.

모든 bounce-back에서 전체 문서를 재검토할 필요는 없다. 영향 선별 후 관련 항목만 확인한다. 단순 내부 수정은 기존 작업 기록과 검증을 재사용한다.

### 비교 기준과 기록

직전 유효 기준 대비 **이번 변경**과, 출발점의 사용자 intent 및 이후 명시적 사용자 결정 대비 **현재의 누적 결과**를 함께 본다. 이전 Root의 선택을 새로운 사용자 intent로 바꾸어 비교 기준을 초기화하지 않는다.

기존 기록에 다음 내용을 짧게 남긴다. 고정된 별도 파일이나 전용 데이터 구조는 요구하지 않는다.

| 항목 | 기록할 내용 |
| --- | --- |
| 기준 | 관련 intent·합의·제품 계약의 실제 원문 위치와 적용 버전 |
| 차이 | 변경·추가·누락·재해석, 새 기본값이나 실패 처리. 차이가 없으면 비교한 보존조건과 이유 |
| 영향과 권한 | 이번·누적 영향, 위임 안의 선택인지, 사용자 결정이 필요한지 |
| 담당 검토와 근거 | Realizer·Contractor 등의 관련 검토, 확보한 증거와 미확보 증거, 필요한 Verifier 재검증 |
| 처리 | 적용 가능, 근거 확보 중, 사용자 결정 대기 등 실제 상황과 영향 작업의 다음 행동 |

위 표현은 기록용 설명이지 새로운 framework 상태 enum(허용 상태값 목록)이 아니다. 실제 상태 변경은 기존 framework를 따른다.

Root가 점검을 준비하되, 중요한 brief 의미·계약 변경의 채택은 담당 agent가 원문과 영향을 보고 검토한다. Root가 작성한 “변경 없음”만으로 담당 검토를 대체하지 않는다. Verifier에게는 유효한 제품 계약과 필요한 변경·영향 정보를 전달하되, 사용자 선호 결정이나 제품 계약 작성 책임을 넘기지 않는다.

## 6. 적용·재시도·전달을 연결한다

Root가 저장하는 brief·계약은 담당 agent가 채택한 내용이어야 한다. 저장 과정에서 의미를 다듬고 싶으면 작성 agent에게 돌려보낸다. 변경된 산출물·구현·계약에 이전 판정을 그대로 붙이지 말고, 담당 agent가 영향 범위에 맞게 판정·증거의 유효성을 확인하도록 한다.

재시도 전에 실패 원인, 달라진 근거·접근, 성공·실패를 확인할 방법을 정리한다. 다음 시도가 의미나 위임 경계를 바꾼다면 먼저 관련 Delta Check를 수행한다. 목적을 바꾸어 문제를 없애지 않는다.

The following two-attempt paragraphs apply to legacy control revision `1.0` and supported historical runs. Control `1.1`/`1.2` runs, including the new-run default `1.2`, follow the selected procedure addendum below.

**현재의 공식 repair 2회 제한은 유지한다.** 초기 계약 준비를 위한 맥락 보충·재검토는 공식 repair에 해당하지 않는 한 횟수를 소비하지 않는다. 다만 이런 활동도 전체 작업 예산과 진전 점검의 대상이다. 별도의 bounce-back 카운터는 요구하지 않는다.

이 문서는 추가 repair 권한을 활성화하지 않는다. 향후 2회를 재평가점으로 바꾸려면 관련 workflow 정책·실행 제어를 별도 개정해야 한다. 그 전에는 자연어 판단으로 기존 제한을 우회하지 않는다.

중요한 자율 결정은 적절한 진행 보고에 그 선택과 실제 영향이 드러나도록 요약한다. 알림은 승인 요청과 구별하며, 사용자 결정이 필요한 사안을 통지만 하고 진행하지 않는다. 최종 전달에는 중요한 자율 결정·변경, 남은 한계, 관련 검토·검증 상태를 모아 보여준다. 내부 로그를 찾아봐야만 알 수 있게 숨기지 않는다.

## 7. 실행 제어와 평가의 경계

아래 항목은 기존 skill·gate를 통해 적용한다. 이 문서나 파일의 존재만으로 의미 보존이 자동 집행되지는 않는다.

- Root 시작·재개에는 공통 instruction과 이 절차, 준비된 인계 또는 직접 요청의 유효 기준을 읽는다. agent에는 담당 원문·조건·미결정·위임과 적용 버전을 실제로 전달한다. Root의 역할 전체를 주입하지 않는다. 준비 경로의 위임 계약과 직접 경로의 필요한 차이 기록을 구별한다.
- 담당 agent의 실제 반환 내용과 Root가 저장한 산출물, 관련 검토·검증 대상 버전이 연결되도록 한다. Root가 작성한 자기 확인 문장만으로 판정의 존재를 인정하지 않는다.
- 중요한 미확정 사항, 필요한 담당 검토·사용자 승인 누락, 변경으로 무효화된 검증이 있으면 관련 단계·최종 전달을 완료 상태로 처리하지 않도록 기존 gate와 연동한다.

실행 명령과 준비/직접 경로의 기존 상태 매핑은
[gate map](../../../../.agents/skills/build-tool-pipeline/references/gate-map.md)을 따른다.
완료 전 PASS를 재검토할 때는 기존 후보 식별을 유지하고 새로운 Verifier 판정을
받는다. 코드·계약을 바꾸어야 하면 정식 repair를 거친다. 이미 완료한 release는
수정하지 않고 revision intake로 처리하며, 이전 archive와 현재 개발 소스를 구별한다.

기계적 검사는 기록 존재·대상 일치·상태 일관성을 확인할 수 있지만, 사용자의 의미가 보존됐는지까지 자동으로 증명하지는 않는다. 해당 의미 판단은 원문과 결과를 보는 담당 검토와 평가 사례로 보완한다.

적용 평가는 제품 품질, 피할 수 있었던 late semantic 질문·재작업, Root 자체 해결, 미승인 중요 변경과 사전 대화·문서화를 포함한 전체 사용자 부담·실행 비용을 함께 본다. 질문 수 감소만으로 성공을 판단하지 않는다. 최소 사례는 다음과 같다. 아래는 평가 설계이며 실제 결과는 별도 평가 기록에 남긴다.

| 사례 | 기대 동작 |
| --- | --- |
| 허용 품질·자원 범위를 모두 만족하는 중요한 기술 선택 | Root가 해결하고 필요한 담당 검토·검증을 받는다. 사용자에게 선택을 떠넘기지 않는다. |
| 관찰한 오차를 근거로 허용 오차를 임의 신설 | 손실 수용의 위임이 없으면 확정하지 않는다. 사용자에게 실질적인 절충을 제시한다. |
| 명시된 intent와 반대로 작성된 계약 | Contractor가 원문에 맞게 수정한다. 수정이라는 이유만으로 사용자 승인을 다시 요구하지 않는다. |
| 입력의 의미를 correction에서 residual로 임의 해석 | 위임 근거가 없는 중요한 의미 선택을 후속 계약·코드에 확정하지 않는다. |
| 작은 기본값 변경들이 합쳐져 의도한 출력이 누락 | 누적 비교에서 발견하고 영향을 받는 선택을 재검토한다. |
| 핵심 예외 조건의 실패를 정상적인 0으로 반환 | 작은 패치·드문 실행이라는 이유로 경미하게 분류하지 않는다. |
| 초기 맥락 보충이 여러 차례 발생 | formal repair로 자동 집계하지 않되 진전·전체 예산을 확인한다. |
| 의미 변경 뒤 이전 PASS를 유지하거나 Root가 계약을 몰래 수정 | 해당 검토·검증의 유효성을 인정하지 않고 담당 역할로 되돌린다. |

## Selected artifact procedure — S7 operating addendum

S7 status annotation: `ITP-20261101-ARTIFACT-S7`, 2026-11-01. This supersedes
the S4 addendum's isolated-trial applicability. Follow the
[selected new-run operating procedure](../contracts/agent-rollout.md), including
the user-authorized post-S7 override `ITP-20261101-DEFAULT12` (2026-11-01):
new runs default to `1.2`; explicit `1.1` remains compatible and new legacy
`1.0` requires explicit selection. Existing runs retain their selectors,
receipts and round history. Preserve the general authority and semantic judgment above.
Use the [invocation procedure](../../../../.agents/skills/build-tool-pipeline/references/invocation.md)
and [control protocol](../contracts/agent-artifact-protocol.md), including the
[recovery clarification](../contracts/round-recovery-clarification.md).

The assigned specialist completes its own submission. Root checks attributable
inputs, exact bytes, boundary and registration outcome without transcribing the
body or routinely repeating specialist judgment. Root still reads the actual
registered contract before implementation. Contractor reads original sources and
the registered brief when supplied; Verifier reads the actual contract and bound
candidate evidence. Compact returns are indexes, never substitute artifacts.
Concrete contradictions, drift, missing evidence or user-reserved choices go to
the responsible owner; no extra routine semantic approval gate is introduced.

Root owns the four post-verification rounds. Reserve one before requesting or
performing subject modification; all related items, contract changes and agent
calls before the next verdict share that round. Initial iteration/verification
and proven unchanged-subject evidence recovery consume no round. Resume retains
the ledger. Early non-progress or intent changes still stop affected work.
After exhaustion, a separate independent process review followed by the user's
explicit finite allowance and changed approach is required. Silence is not
approval; no count reset, replacement run, weaker quality gate or automatic
continuation is permitted. A fourth passing result may proceed normally.

This procedure does not make generic role semantics pipeline-dependent or alter
legacy counts, completed releases, models, nested-delegation limits or role
independence. Retain a compatible installation before procedure-byte updates or
rollback, recover interrupted transactions against original project/run paths,
and obtain fresh owner assignments/bindings before forward use. Old bindings,
hashes, receipts and round records remain historical evidence; never rewrite
them to match updated procedures. S7 itself grants no migration, release,
baseline promotion or additional-round permission. The original S4 source and
live-check status remains in the
[S4 checkpoint](../../workspace/framework_development/aa-impl/s4-checkpoint.md).

## Revision history

### 2026-09-13 — TW-20260913-P2/P3

- 근거: 전환 계획 및 순차 개정 요청. v0.2는 보존한다.
- 차이: 모든 제작 시작에 위임을 신규 작성하던 가정을 제거했다. A 준비·인계, B 준비본 소비/직접 진입·국소 반환으로 절차를 재배치했다.
- 보존: 중요도와 위임 구분, 개별·누적 Delta Check, 담당 채택과 저장·판정 연결, formal repair 2회와 중단·보고 원칙.
- 영향/호환성: 세 문서, 두 skill, contractor intake, 기존 제어·완료 보고. 새 권한·agent·state enum은 도입하지 않는다.
- 검증·한계: [단계별 평가 기록 (source history)](../provenance.md)에 실제 완료한 인계 시험과 통합 검증을 기록한다.
