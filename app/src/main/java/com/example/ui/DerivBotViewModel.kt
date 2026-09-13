package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.DerivBotRepository
import com.example.model.*
import com.example.notification.BotNotificationManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class UiState(
    val selectedTab: Int = 0, // 0: Dashboard, 1: Live Trades, 2: Technical Signals, 3: Risk Controls
    val selectedSymbol: String = "Volatility 100 (1s) Index (R_100)",
    val stakeInput: Double = 10.0,
    val isExecuting: Boolean = false,
    val userNotificationMessage: String? = null
)

class DerivBotViewModel(application: Application) : AndroidViewModel(application) {

    private val notificationManager = BotNotificationManager(application)
    private val repository = DerivBotRepository(notificationManager)

    val botStatus: StateFlow<BotStatus> = repository.botStatus
    val derivLink: StateFlow<DerivLinkStatus> = repository.derivLink
    val riskState: StateFlow<RiskState> = repository.riskState
    val trades: StateFlow<List<Trade>> = repository.trades
    val signals: StateFlow<List<TradeSignal>> = repository.signals

    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    fun selectTab(tab: Int) {
        _uiState.value = _uiState.value.copy(selectedTab = tab)
    }

    fun selectSymbol(symbol: String) {
        _uiState.value = _uiState.value.copy(selectedSymbol = symbol)
    }

    fun updateStake(stake: Double) {
        _uiState.value = _uiState.value.copy(stakeInput = stake)
    }

    fun dismissToast() {
        _uiState.value = _uiState.value.copy(userNotificationMessage = null)
    }

    fun toggleBotState() {
        if (botStatus.value == BotStatus.RUNNING) {
            repository.pauseBot()
            _uiState.value = _uiState.value.copy(userNotificationMessage = "Bot PAUSED. Autonomous execution suspended.")
        } else {
            repository.resumeBot()
            _uiState.value = _uiState.value.copy(userNotificationMessage = "Bot RESUMED. Autonomous execution running 24/7 on Cloud Run.")
        }
    }

    fun requestManualTrade(action: String) {
        val current = _uiState.value
        _uiState.value = current.copy(isExecuting = true)

        viewModelScope.launch {
            val result = repository.requestTrade(
                symbol = current.selectedSymbol,
                contractType = action,
                stake = current.stakeInput
            )
            result.onSuccess { msg ->
                _uiState.value = _uiState.value.copy(
                    isExecuting = false,
                    userNotificationMessage = "✅ $msg"
                )
            }.onFailure { err ->
                _uiState.value = _uiState.value.copy(
                    isExecuting = false,
                    userNotificationMessage = "🚨 ${err.message}"
                )
            }
        }
    }
}
