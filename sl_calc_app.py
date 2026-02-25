import streamlit as st

st.set_page_config(page_title="Multi-Entry SL 역산 계산기", layout="centered")

st.title("여러 타점 + 수량 기반 SL 역산 계산기 (롱/숏 공통, 총 시드 리스크 고정)")

st.markdown("""
- **상황 예시**: 이미 1차 진입이 들어가 있고, 추가매수를 여러 개(2차, 3차, 4차...)로 걸어둔 상태
- **입력**: 각 타점의 **진입가 + 코인 수량(예: BTC 개수)** 를 직접 입력
- **목표**: SL에 도달했을 때 **총 시드의 리스크 %만 손실** 나도록 SL 가격을 역산
- **가정**: USDT 선형 선물, 수수료/슬리피지는 미반영 (PnL만 기준)
""")

# ----- Inputs -----
colA, colB = st.columns(2)

with colA:
    S = st.number_input("총 시드 S (USDT, 지갑 기준)", min_value=1.0, value=1000.0, step=50.0)
    side = st.selectbox("포지션 방향", ["long", "short"])
    L = st.number_input("레버리지 L (참고용, 손익 계산엔 직접 영향 없음)", min_value=1.0, value=5.0, step=1.0)

with colB:
    risk_pct = st.number_input("1회 최대손실(총시드 %) (예: 10)", min_value=0.1, value=10.0, step=0.5)
    risk = risk_pct / 100.0
    R = st.number_input("TP R배수 (예: 2 = 2R)", min_value=0.1, value=2.0, step=0.1)

st.subheader("진입 타점 & 수량 (코인 기준)")
st.caption("예: 이미 진입된 포지션 + 대기중인 추가매수/추가진입까지 모두 포함해서 적어주세요.")

num_entries = st.number_input("진입 타점/포지션 개수", min_value=1, max_value=10, value=4, step=1)

entries = []
total_notional = 0.0
total_qty = 0.0

for i in range(int(num_entries)):
    c1, c2 = st.columns(2)
    with c1:
        price = st.number_input(
            f"{i+1}차 진입가",
            min_value=0.00000001,
            value=65000.0,
            step=10.0,
            format="%.8f",
            key=f"price_{i}",
        )
    with c2:
        qty = st.number_input(
            f"{i+1}차 수량 (BTC 등)",
            min_value=0.0,
            value=0.0,
            step=0.0001,
            format="%.6f",
            key=f"qty_{i}",
        )
    entries.append((price, qty))
    total_notional += price * qty
    total_qty += qty

st.divider()

if total_qty <= 0:
    st.error("수량이 0입니다. 각 타점의 수량을 하나 이상 입력해 주세요.")
    st.stop()

avg = total_notional / total_qty

# ----- SL 역산 (수량 기반) -----
# 롱 포지션:
#   손실 = Σ q_i (p_i - SL) = S * risk
#   SL_long = (Σ q_i p_i - S*risk) / Σ q_i
# 숏 포지션:
#   손실 = Σ q_i (SL - p_i) = S * risk
#   SL_short = (S*risk + Σ q_i p_i) / Σ q_i

if side == "long":
    SL = (total_notional - S * risk) / total_qty
else:
    SL = (S * risk + total_notional) / total_qty

if SL <= 0:
    st.error("계산된 SL이 0 이하입니다. 시드/리스크/포지션 사이즈를 다시 확인해 주세요.")
    st.stop()

# ----- 실제 손실 재계산 (검증용) -----
gross_loss = 0.0
for price, qty in entries:
    if side == "long":
        gross_loss += max(0.0, (price - SL) * qty)
    else:
        gross_loss += max(0.0, (SL - price) * qty)

loss_pct = (gross_loss / S) * 100.0

# ----- TP 계산 (R배수, 평단 기준) -----
risk_dist = abs(avg - SL)
if side == "long":
    TP = avg + R * risk_dist
    TP_1R = avg + risk_dist
else:
    TP = avg - R * risk_dist
    TP_1R = avg - risk_dist

# ----- 마진/레버리지 참고값 -----
margin_est = total_notional / L
margin_pct_of_seed = (margin_est / S) * 100.0

# ----- 결과 출력 -----
st.subheader("결과")

c1, c2, c3 = st.columns(3)
c1.metric("총 수량 (Q)", f"{total_qty:.6f}")
c2.metric("총 노출(Notional)", f"{total_notional:.2f} USDT")
c3.metric("예상 필요 마진(대략)", f"{margin_est:.2f} USDT ({margin_pct_of_seed:.1f}% of S)")

c4, c5, c6 = st.columns(3)
c4.metric("평단(Avg)", f"{avg:.8f}")
c5.metric("손절가(SL, 역산값)", f"{SL:.8f}")
c6.metric("테이크프로핏(TP)", f"{TP:.8f}  ({R:.1f}R)")

st.caption(f"참고: 1R 라인 = {TP_1R:.8f}")

st.subheader("리스크 체크 (1회 트레이드 기준)")
cc1, cc2, cc3 = st.columns(3)
cc1.metric("설정한 최대손실", f"{S * risk:.2f} USDT ({risk_pct:.1f}%)")
cc2.metric("SL 도달 시 실제손실(이론)", f"{gross_loss:.2f} USDT ({loss_pct:.2f}%)")
cc3.metric("레버리지 (입력값)", f"{L:.2f}x")

with st.expander("입력 타점/수량 상세"):
    for i, (price, qty) in enumerate(entries, start=1):
        st.write(f"- {i}차: 진입가 {price:.8f} / 수량 {qty:.6f}")
    st.write(f"- 포지션 평단 Avg: {avg:.8f}")
    st.write(f"- 롱/숏 방향: {side}")

