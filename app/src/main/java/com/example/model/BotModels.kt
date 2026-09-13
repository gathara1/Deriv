package com.example.model

enum class TradeStatus {
    OPEN,
    WON,
    LOST,
    FAILED
}

enum class BotStatus {
    RUNNING,
    PAUSED
}

data class DerivLinkStatus(
    val linked: Boolean = true,
    val accountId: String = "VRTC1092831",
    val isVirtual: Boolean = true,
    val currency: String = "USD",
    val balance: Double = 10000.0,
    val lastSynced: String = "Live WebSocket Sync",
    val lastError: String? = null
)

data class RiskViolation(
    val timestamp: String,
    val reason: String,
    val stake: Double,
    val symbol: String,
    val action: String
)

data class RiskState(
    val maxDailyLossPct: Double = 5.0,
    val maxConcurrentContracts: Int = 3,
    val maxStakePerTrade: Double = 25.0,
    val dailyLossCounter: Double = 10.0,
    val startingDailyBalance: Double = 1000.0,
    val openContractsCount: Int = 1,
    val lastResetDate: String = "2026-09-12",
    val violationsHistory: List<RiskViolation> = listOf(
        RiskViolation(
            timestamp = "14:23 UTC",
            reason = "Stake $35.00 exceeds max stake ceiling of $25.00",
            stake = 35.0,
            symbol = "R_100",
            action = "CALL"
        )
    )
) {
    val currentDailyLossPct: Double
        get() = if (startingDailyBalance > 0) (dailyLossCounter / startingDailyBalance) * 100.0 else 0.0
}

data class Trade(
    val id: String,
    val contractId: Long?,
    val proposalId: String?,
    val symbol: String,
    val contractType: String, // "CALL" or "PUT"
    val stake: Double,
    val payout: Double,
    val entrySpot: Double,
    val exitSpot: Double? = null,
    val status: TradeStatus,
    val profit: Double? = null,
    val purchaseTime: Long? = null,
    val shortcode: String? = null,
    val duration: String = "5t",
    val openedAt: String,
    val closedAt: String? = null,
    val rawError: String? = null
)

data class IndicatorSnapshot(
    val rsi: Double,
    val emaFast: Double,
    val emaSlow: Double,
    val bollingerUpper: Double,
    val bollingerMiddle: Double,
    val bollingerLower: Double,
    val bollingerPctB: Double,
    val currentPrice: Double
)

data class TradeSignal(
    val id: String,
    val symbol: String,
    val action: String, // "CALL" or "PUT"
    val confidencePct: Double,
    val strategyName: String,
    val indicators: IndicatorSnapshot,
    val formulaBreakdown: String,
    val geminiExplanation: String?,
    val timestamp: String
)
