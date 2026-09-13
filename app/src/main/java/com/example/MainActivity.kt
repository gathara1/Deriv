package com.example

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.model.BotStatus
import com.example.ui.DerivBotViewModel
import com.example.ui.components.*
import com.example.ui.theme.*

class MainActivity : ComponentActivity() {

    private val viewModel: DerivBotViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            DerivBotTheme {
                // Request Notification Permission on Android 13+
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    val permissionLauncher = rememberLauncherForActivityResult(
                        contract = ActivityResultContracts.RequestPermission()
                    ) { _ -> }

                    LaunchedEffect(Unit) {
                        val hasPermission = ContextCompat.checkSelfPermission(
                            this@MainActivity,
                            Manifest.permission.POST_NOTIFICATIONS
                        ) == PackageManager.PERMISSION_GRANTED
                        if (!hasPermission) {
                            permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                        }
                    }
                }

                DerivBotApp(viewModel = viewModel)
            }
        }
    }
}

@Composable
fun DerivBotApp(viewModel: DerivBotViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val botStatus by viewModel.botStatus.collectAsStateWithLifecycle()
    val linkStatus by viewModel.derivLink.collectAsStateWithLifecycle()
    val riskState by viewModel.riskState.collectAsStateWithLifecycle()
    val trades by viewModel.trades.collectAsStateWithLifecycle()
    val signals by viewModel.signals.collectAsStateWithLifecycle()

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.userNotificationMessage) {
        uiState.userNotificationMessage?.let { msg ->
            snackbarHostState.showSnackbar(
                message = msg,
                duration = SnackbarDuration.Short
            )
            viewModel.dismissToast()
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = TerminalBackground,
        contentWindowInsets = WindowInsets.safeDrawing,
        snackbarHost = {
            SnackbarHost(
                hostState = snackbarHostState,
                snackbar = { data ->
                    Snackbar(
                        containerColor = TerminalCard,
                        contentColor = TextPrimary,
                        shape = MaterialTheme.shapes.small,
                        modifier = Modifier.padding(12.dp)
                    ) {
                        Text(
                            text = data.visuals.message,
                            style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace)
                        )
                    }
                }
            )
        },
        topBar = {
            TopBarAndHeader(
                botStatus = botStatus,
                linkStatus = linkStatus,
                onToggleBot = { viewModel.toggleBotState() }
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = TerminalSurface,
                tonalElevation = 8.dp,
                windowInsets = WindowInsets.navigationBars
            ) {
                val navItems = listOf(
                    Triple(0, "Terminal", Icons.Default.Terminal),
                    Triple(1, "Trades", Icons.Default.ReceiptLong),
                    Triple(2, "Signals", Icons.Default.Sensors),
                    Triple(3, "Risk Guard", Icons.Default.Shield)
                )

                navItems.forEach { (index, title, icon) ->
                    val isSelected = uiState.selectedTab == index
                    NavigationBarItem(
                        selected = isSelected,
                        onClick = { viewModel.selectTab(index) },
                        icon = {
                            Icon(
                                imageVector = icon,
                                contentDescription = title,
                                modifier = Modifier.size(20.dp)
                            )
                        },
                        label = {
                            Text(
                                text = title,
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 11.sp
                                )
                            )
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = NeonCyan,
                            selectedTextColor = NeonCyan,
                            indicatorColor = CyanAlpha10,
                            unselectedIconColor = TextSecondary,
                            unselectedTextColor = TextMuted
                        ),
                        modifier = Modifier.testTag("nav_item_$index")
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(TerminalBackground)
        ) {
            when (uiState.selectedTab) {
                0 -> TerminalTab(
                    uiState = uiState,
                    riskState = riskState,
                    latestSignal = signals.firstOrNull(),
                    recentTrade = trades.firstOrNull(),
                    onRequestTrade = { action -> viewModel.requestManualTrade(action) },
                    onSelectSymbol = { sym -> viewModel.selectSymbol(sym) },
                    onUpdateStake = { stake -> viewModel.updateStake(stake) },
                    onViewAllTrades = { viewModel.selectTab(1) },
                    onViewAllSignals = { viewModel.selectTab(2) }
                )

                1 -> TradesTab(trades = trades)

                2 -> SignalsTab(signals = signals)

                3 -> RiskTab(riskState = riskState)
            }
        }
    }
}
