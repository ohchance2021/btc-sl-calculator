import streamlit as st
import pandas as pd
from datetime import datetime

st.title("트레이딩 일지 (MVP)")

st.markdown("""
- **목표**: 각 트레이드를 간단히 기록하면서, **승률 / 손익비 / R** 를 자동으로 요약해서 보여주는 일지
- 현재 버전은 **앱이 켜져 있는 동안** 데이터가 유지됩니다. 중요한 기록은 **CSV로 다운로드해서 보관**해 주세요.
""")

# ----- 초기 상태 -----
if "journal" not in st.session_state:
    st.session_state.journal = pd.DataFrame(
        columns=[
            "date",
            "exchange",
            "symbol",
            "side",
            "strategy",
            "leverage",
            "account_equity",
            "entry_price",
            "planned_sl",
            "planned_tp",
            "exit_price",
            "position_size",
            "pnl_usd",
            "pnl_pct",
            "r_multiple",
            "tags",
            "notes",
        ]
    )

journal_df = st.session_state.journal

st.subheader("새 트레이드 기록")

with st.form("new_trade"):
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input("날짜", datetime.now())
        exchange = st.text_input("거래소", value="Gate.io")
        symbol = st.text_input("심볼 (예: BTCUSDT)", value="BTCUSDT")

    with col2:
        side = st.selectbox("방향", ["long", "short"])
        strategy = st.text_input("전략/세팅 이름", value="3-entry swing")
        leverage = st.number_input("레버리지", min_value=1.0, value=5.0, step=1.0)

    with col3:
        account_equity = st.number_input("당시 계정 시드 (USDT)", min_value=1.0, value=1000.0, step=50.0)
        position_size = st.number_input("포지션 수량 (BTC 등)", min_value=0.0, value=0.01, step=0.001, format="%.6f")

    st.markdown("#### 가격 / 리스크 설정")
    c4, c5, c6, c7 = st.columns(4)
    with c4:
        entry_price = st.number_input("진입 평단", min_value=0.00000001, value=65000.0, step=10.0, format="%.8f")
    with c5:
        planned_sl = st.number_input("계획 SL", min_value=0.00000001, value=64000.0, step=10.0, format="%.8f")
    with c6:
        planned_tp = st.number_input("계획 TP", min_value=0.00000001, value=67000.0, step=10.0, format="%.8f")
    with c7:
        exit_price = st.number_input("실제 청산가 (전체 기준)", min_value=0.00000001, value=66000.0, step=10.0, format="%.8f")

    st.markdown("#### 실행 / 피드백")
    tags = st.multiselect(
        "태그 (해당되는 것들 선택)",
        options=[
            "계획대로",
            "조기 익절",
            "손절 미이행",
            "과도 진입",
            "진입 지연",
            "감정 트레이딩",
            "좋은 손절",
        ],
    )
    notes = st.text_area("메모 / 피드백 (한두 줄이라도 적기)", height=80)

    submitted = st.form_submit_button("트레이드 추가")

    if submitted:
        if position_size <= 0:
            st.error("포지션 수량을 0보다 크게 입력해 주세요.")
        else:
            # 손익 및 R 계산
            if side == "long":
                pnl_usd = (exit_price - entry_price) * position_size
                risk_per_unit = abs(entry_price - planned_sl)
            else:
                pnl_usd = (entry_price - exit_price) * position_size
                risk_per_unit = abs(planned_sl - entry_price)

            risk_amt = risk_per_unit * position_size
            if risk_amt > 0:
                r_multiple = pnl_usd / risk_amt
            else:
                r_multiple = 0.0

            pnl_pct = (pnl_usd / account_equity) * 100.0

            new_row = {
                "date": date.strftime("%Y-%m-%d"),
                "exchange": exchange,
                "symbol": symbol,
                "side": side,
                "strategy": strategy,
                "leverage": leverage,
                "account_equity": account_equity,
                "entry_price": entry_price,
                "planned_sl": planned_sl,
                "planned_tp": planned_tp,
                "exit_price": exit_price,
                "position_size": position_size,
                "pnl_usd": pnl_usd,
                "pnl_pct": pnl_pct,
                "r_multiple": r_multiple,
                "tags": ", ".join(tags),
                "notes": notes,
            }

            st.session_state.journal = pd.concat(
                [st.session_state.journal, pd.DataFrame([new_row])],
                ignore_index=True,
            )
            st.success("트레이드가 일지에 추가되었습니다.")

journal_df = st.session_state.journal

st.divider()
st.subheader("일지 요약 / 통계")

if len(journal_df) == 0:
    st.info("아직 기록된 트레이드가 없습니다. 위 폼을 사용해서 첫 기록을 추가해 보세요.")
else:
    wins = journal_df[journal_df["pnl_usd"] > 0]
    losses = journal_df[journal_df["pnl_usd"] < 0]

    total_trades = len(journal_df)
    win_rate = len(wins) / total_trades * 100.0 if total_trades > 0 else 0.0
    avg_r = journal_df["r_multiple"].mean() if total_trades > 0 else 0.0
    avg_r_win = wins["r_multiple"].mean() if len(wins) > 0 else 0.0
    avg_r_loss = losses["r_multiple"].mean() if len(losses) > 0 else 0.0
    total_pnl = journal_df["pnl_usd"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("총 트레이드 수", total_trades)
    c2.metric("승률", f"{win_rate:.1f}%")
    c3.metric("평균 R", f"{avg_r:.2f}R")
    c4.metric("이긴 트레이드 평균 R", f"{avg_r_win:.2f}R")
    c5.metric("진 트레이드 평균 R", f"{avg_r_loss:.2f}R")

    c6, c7 = st.columns(2)
    c6.metric("총 PNL (USDT)", f"{total_pnl:.2f}")
    if total_trades > 0:
        expectancy = avg_r
        c7.metric("기대값 (트레이드당 평균 R)", f"{expectancy:.2f}R")

    st.subheader("트레이드 리스트")
    st.dataframe(journal_df, use_container_width=True)

    csv = journal_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="CSV로 다운로드 (백업용)",
        data=csv,
        file_name="trading_journal.csv",
        mime="text/csv",
    )
