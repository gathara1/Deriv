package com.example.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.*
import com.example.ui.UiState
import com.example.ui.theme.*
import java.util.Locale

@Composable
fun TerminalTab(
    uiState: UiState,
    riskState: RiskState,
    latestSignal: TradeSignal?,
    recentTrade: Trade?,
    onRequestTrade: (action: String) -> Unit,
    onSelectSymbol: (String) -> Unit,
    onUpdateStake: (Double) -> Unit,
    onViewAllTrades: () -> Unit,
    onViewAllSignals: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Architecture & Cloud Run Independence Card
        Surface(
            color = TerminalCard,
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, TerminalCardBorder, RoundedCornerShape(12.dp))
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.AllInclusive,
                        contentDescription = "Independent 24/7 Execution",
                        tint = NeonCyan,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "CLOUD RUN 24/7 INDEPENDENT SERVICE",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 1.sp
                        ),
                        color = NeonCyan
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Closing this app NEVER stops the bot. The persistent Python service maintains Deriv WebSocket connection and executes deterministic signals automatically. Reopening syncs latest state.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )
            }
        }

        // Quick Execution Pad (Client Surface: requestTrade Callable)
        Surface(
            color = TerminalSurface,
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, TerminalCardBorder, RoundedCornerShape(12.dp))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "CALLABLE TRADE DISPATCH",
                        style = MaterialTheme.typography.labelLarge.copy(
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 1.sp
                        ),
                        color = TextPrimary
                    )
                    Text(
                        text = "requestTrade()",
                        style = MaterialTheme.typography.labelSmall.copy(fontFamily = FontFamily.Monospace),
                        color = TextMuted
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Symbol Selector
                Text(
                    text = "SELECT ASSET",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val symbols = listOf(
                        "Volatility 100 (1s) Index (R_100)",
                        "Volatility 75 Index (R_75)",
                        "Volatility 50 Index (R_50)"
                    )
                    symbols.forEach { sym ->
                        val isSelected = uiState.selectedSymbol == sym
                        val shortLabel = if (sym.contains("100")) "R_100" else if (sym.contains("75")) "R_75" else "R_50"
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isSelected) CyanAlpha10 else TerminalCard)
                                .border(
                                    1.dp,
                                    if (isSelected) NeonCyan else TerminalCardBorder,
                                    RoundedCornerShape(8.dp)
                                )
                                .clickable { onSelectSymbol(sym) }
                                .padding(vertical = 10.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = shortLabel,
                                style = MaterialTheme.typography.bodyMedium.copy(
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    fontFamily = FontFamily.Monospace
                                ),
                                color = if (isSelected) NeonCyan else TextSecondary
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Stake Selector
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "TRADE STAKE (MAX $25.00)",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                        color = TextSecondary
                    )
                    Text(
                        text = "$${uiState.stakeInput} USD",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        ),
                        color = if (uiState.stakeInput > riskState.maxStakePerTrade) DangerRed else NeonCyan
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val stakes = listOf(5.0, 10.0, 25.0, 50.0)
                    stakes.forEach { s ->
                        val isSelected = uiState.stakeInput == s
                        val isViolation = s > riskState.maxStakePerTrade
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(
                                    when {
                                        isSelected && isViolation -> RedAlpha10
                                        isSelected -> CyanAlpha10
                                        else -> TerminalCard
                                    }
                                )
                                .border(
                                    1.dp,
                                    when {
                                        isSelected && isViolation -> DangerRed
                                        isSelected -> NeonCyan
                                        isViolation -> DangerRed.copy(alpha = 0.5f)
                                        else -> TerminalCardBorder
                                    },
                                    RoundedCornerShape(8.dp)
                                )
                                .clickable { onUpdateStake(s) }
                                .padding(vertical = 8.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(
                                    text = "$$s",
                                    style = MaterialTheme.typography.bodySmall.copy(
                                        fontWeight = FontWeight.Bold,
                                        fontFamily = FontFamily.Monospace
                                    ),
                                    color = if (isViolation) DangerRed else if (isSelected) NeonCyan else TextPrimary
                                )
                                if (isViolation) {
                                    Text(
                                        text = "TEST LIMIT",
                                        style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.sp),
                                        color = DangerRed
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Execution Buttons: BUY CALL / BUY PUT
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Button(
                        onClick = { onRequestTrade("CALL") },
                        enabled = !uiState.isExecuting,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = NeonEmerald,
                            contentColor = Color.Black
                        ),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp)
                            .testTag("request_call_button")
                    ) {
                        Icon(Icons.Default.TrendingUp, contentDescription = "Buy Call", modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "BUY CALL",
                            style = MaterialTheme.typography.labelLarge.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            )
                        )
                    }

                    Button(
                        onClick = { onRequestTrade("PUT") },
                        enabled = !uiState.isExecuting,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = DangerRed,
                            contentColor = Color.White
                        ),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp)
                            .testTag("request_put_button")
                    ) {
                        Icon(Icons.Default.TrendingDown, contentDescription = "Buy Put", modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "BUY PUT",
                            style = MaterialTheme.typography.labelLarge.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            )
                        )
                    }
                }
            }
        }

        // Live Risk Snapshot Card
        Surface(
            color = TerminalSurface,
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, TerminalCardBorder, RoundedCornerShape(12.dp))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Security,
                            contentDescription = "Risk Guard",
                            tint = WarningAmber,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "RISK MODULE (PRE-TRADE GUARD)",
                            style = MaterialTheme.typography.labelMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            ),
                            color = TextPrimary
                        )
                    }
                    Text(
                        text = "Strict Enforce",
                        style = MaterialTheme.typography.labelSmall,
                        color = NeonEmerald
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(text = "Daily Drawdown", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(
                            text = "${String.format(Locale.US, "%.1f", riskState.currentDailyLossPct)}% / ${riskState.maxDailyLossPct}% max",
                            style = MaterialTheme.typography.bodyMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            ),
                            color = if (riskState.currentDailyLossPct >= riskState.maxDailyLossPct) DangerRed else TextPrimary
                        )
                    }

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(text = "Open Contracts", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(
                            text = "${riskState.openContractsCount} / ${riskState.maxConcurrentContracts} max",
                            style = MaterialTheme.typography.bodyMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            ),
                            color = if (riskState.openContractsCount >= riskState.maxConcurrentContracts) WarningAmber else TextPrimary
                        )
                    }

                    Column(horizontalAlignment = Alignment.End) {
                        Text(text = "Stake Ceiling", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(
                            text = "$${riskState.maxStakePerTrade}",
                            style = MaterialTheme.typography.bodyMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            ),
                            color = NeonCyan
                        )
                    }
                }
            }
        }

        // Latest Deterministic Signal with Gemini Rationale
        if (latestSignal != null) {
            Surface(
                color = TerminalSurface,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, TerminalCardBorder, RoundedCornerShape(12.dp))
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(if (latestSignal.action == "CALL") GreenAlpha10 else RedAlpha10)
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = latestSignal.action,
                                    style = MaterialTheme.typography.labelMedium.copy(
                                        fontWeight = FontWeight.Bold,
                                        fontFamily = FontFamily.Monospace
                                    ),
                                    color = if (latestSignal.action == "CALL") NeonEmerald else DangerRed
                                )
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "${latestSignal.confidencePct}% Confluence",
                                style = MaterialTheme.typography.labelMedium.copy(
                                    fontWeight = FontWeight.Bold,
                                    fontFamily = FontFamily.Monospace
                                ),
                                color = NeonCyan
                            )
                        }
                        Text(
                            text = latestSignal.timestamp,
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = latestSignal.strategyName,
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = latestSignal.formulaBreakdown,
                        style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                        color = TextMuted
                    )

                    // Gemini Plain-English Technical Explanation
                    if (!latestSignal.geminiExplanation.isNullOrBlank()) {
                        Spacer(modifier = Modifier.height(10.dp))
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .background(TerminalCard)
                                .border(1.dp, CyanAlpha10, RoundedCornerShape(8.dp))
                                .padding(10.dp)
                        ) {
                            Column {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.AutoAwesome,
                                        contentDescription = "Gemini Explanation",
                                        tint = NeonCyan,
                                        modifier = Modifier.size(14.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = "GEMINI SERVER EXPLANATION",
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            fontWeight = FontWeight.Bold,
                                            fontFamily = FontFamily.Monospace
                                        ),
                                        color = NeonCyan
                                    )
                                }
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = latestSignal.geminiExplanation,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
