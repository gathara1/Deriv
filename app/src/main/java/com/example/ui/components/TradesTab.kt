package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.Trade
import com.example.model.TradeStatus
import com.example.ui.theme.*
import java.util.Locale

@Composable
fun TradesTab(
    trades: List<Trade>,
    modifier: Modifier = Modifier
) {
    var filterStatus by remember { mutableStateOf<TradeStatus?>(null) }

    val filteredTrades = remember(trades, filterStatus) {
        if (filterStatus == null) trades else trades.filter { it.status == filterStatus }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Filter Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChipItem(
                label = "ALL (${trades.size})",
                selected = filterStatus == null,
                onClick = { filterStatus = null }
            )
            FilterChipItem(
                label = "OPEN (${trades.count { it.status == TradeStatus.OPEN }})",
                selected = filterStatus == TradeStatus.OPEN,
                onClick = { filterStatus = TradeStatus.OPEN }
            )
            FilterChipItem(
                label = "SETTLED (${trades.count { it.status == TradeStatus.WON || it.status == TradeStatus.LOST }})",
                selected = filterStatus == TradeStatus.WON || filterStatus == TradeStatus.LOST,
                onClick = { filterStatus = TradeStatus.WON }
            )
            FilterChipItem(
                label = "FAILED (${trades.count { it.status == TradeStatus.FAILED }})",
                selected = filterStatus == TradeStatus.FAILED,
                onClick = { filterStatus = TradeStatus.FAILED }
            )
        }

        Spacer(modifier = Modifier.height(14.dp))

        if (filteredTrades.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(32.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = Icons.Default.ReceiptLong,
                        contentDescription = "No Trades",
                        tint = TextMuted,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "No trades match this filter",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary
                    )
                    Text(
                        text = "Autonomous trades from Cloud Run appear here in real-time.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextMuted
                    )
                }
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier
                    .fillMaxSize()
                    .testTag("trades_list")
            ) {
                items(filteredTrades, key = { it.id }) { trade ->
                    TradeCard(trade = trade)
                }
            }
        }
    }
}

@Composable
private fun FilterChipItem(
    label: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(if (selected) CyanAlpha10 else TerminalCard)
            .border(
                1.dp,
                if (selected) NeonCyan else TerminalCardBorder,
                RoundedCornerShape(6.dp)
            )
            .clickable { onClick() }
            .padding(horizontal = 10.dp, vertical = 6.dp)
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
                fontFamily = FontFamily.Monospace
            ),
            color = if (selected) NeonCyan else TextSecondary
        )
    }
}

@Composable
fun TradeCard(trade: Trade) {
    val statusColor = when (trade.status) {
        TradeStatus.OPEN -> NeonCyan
        TradeStatus.WON -> NeonEmerald
        TradeStatus.LOST -> DangerRed
        TradeStatus.FAILED -> WarningAmber
    }

    Surface(
        color = TerminalSurface,
        shape = RoundedCornerShape(10.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, TerminalCardBorder, RoundedCornerShape(10.dp))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Header: Symbol, Action Badge, Status
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(if (trade.contractType == "CALL") GreenAlpha10 else RedAlpha10)
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = trade.contractType,
                            style = MaterialTheme.typography.labelSmall.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            ),
                            color = if (trade.contractType == "CALL") NeonEmerald else DangerRed
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = trade.symbol,
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                        color = TextPrimary
                    )
                }

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(statusColor.copy(alpha = 0.12f))
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                ) {
                    Text(
                        text = trade.status.name,
                        style = MaterialTheme.typography.labelSmall.copy(
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        ),
                        color = statusColor
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // IDs and Timestamps
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = if (trade.contractId != null) "Contract #${trade.contractId}" else "No contract (Pre-buy failed)",
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = FontFamily.Monospace),
                    color = TextMuted
                )
                Text(
                    text = trade.openedAt,
                    style = MaterialTheme.typography.labelSmall,
                    color = TextMuted
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Details: Stake, Payout, Entry/Exit Spot, P&L
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(text = "STAKE", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                    Text(
                        text = "$${trade.stake}",
                        style = MaterialTheme.typography.bodyMedium.copy(
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        ),
                        color = TextPrimary
                    )
                }

                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(text = "ENTRY / EXIT", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                    Text(
                        text = "${trade.entrySpot} / ${trade.exitSpot ?: "Active"}",
                        style = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace),
                        color = TextSecondary
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(text = "NET P&L", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                    if (trade.profit != null) {
                        val isPos = trade.profit >= 0
                        Text(
                            text = (if (isPos) "+$" else "-$") + String.format(Locale.US, "%.2f", Math.abs(trade.profit)),
                            style = MaterialTheme.typography.bodyMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            ),
                            color = if (isPos) NeonEmerald else DangerRed
                        )
                    } else if (trade.status == TradeStatus.OPEN) {
                        Text(
                            text = "Potential +$${(trade.payout - trade.stake)}",
                            style = MaterialTheme.typography.bodyMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace
                            ),
                            color = NeonCyan
                        )
                    } else {
                        Text(
                            text = "$0.00",
                            style = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace),
                            color = TextMuted
                        )
                    }
                }
            }

            // Raw Error Display for FAILED Trades (Strict requirement)
            if (!trade.rawError.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(6.dp))
                        .background(RedAlpha10)
                        .border(1.dp, DangerRed.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                        .padding(8.dp)
                ) {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.ErrorOutline,
                                contentDescription = "Deriv API Error",
                                tint = DangerRed,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "RAW DERIV API REJECTION",
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    fontFamily = FontFamily.Monospace
                                ),
                                color = DangerRed
                            )
                        }
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = trade.rawError,
                            style = MaterialTheme.typography.bodySmall.copy(
                                fontFamily = FontFamily.Monospace,
                                fontSize = 11.sp
                            ),
                            color = TextPrimary
                        )
                    }
                }
            }
        }
    }
}
