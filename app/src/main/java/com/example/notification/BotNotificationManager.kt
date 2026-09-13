package com.example.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.example.MainActivity
import com.example.model.TradeStatus

class BotNotificationManager(private val context: Context) {

    companion object {
        const val CHANNEL_ID = "deriv_bot_channel"
        const val CHANNEL_NAME = "Deriv Trading Bot Alerts"
    }

    init {
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val importance = NotificationManager.IMPORTANCE_HIGH
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                importance
            ).apply {
                description = "Real-time alerts for Deriv trades opened, closed, and risk limit warnings."
                enableVibration(true)
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
            notificationManager?.createNotificationChannel(channel)
        }
    }

    private fun getPendingIntent(): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        return PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    fun notifyTradeOpened(symbol: String, action: String, contractId: Long, stake: Double) {
        try {
            val builder = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_more)
                .setContentTitle("🎯 Trade Opened ($action)")
                .setContentText("$symbol #$contractId executed with stake $$stake")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(getPendingIntent())
                .setAutoCancel(true)

            val notificationManager = NotificationManagerCompat.from(context)
            notificationManager.notify((System.currentTimeMillis() % 10000).toInt(), builder.build())
        } catch (_: SecurityException) {
            // Notification permission denied or not yet granted
        }
    }

    fun notifyTradeClosed(symbol: String, status: TradeStatus, profit: Double, contractId: Long) {
        try {
            val isWon = status == TradeStatus.WON
            val title = if (isWon) "🏆 Trade WON" else "📉 Trade Settled (Loss)"
            val profitFormatted = if (profit >= 0) "+$$profit" else "-$${Math.abs(profit)}"

            val builder = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_more)
                .setContentTitle(title)
                .setContentText("$symbol #$contractId: P&L $profitFormatted")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(getPendingIntent())
                .setAutoCancel(true)

            val notificationManager = NotificationManagerCompat.from(context)
            notificationManager.notify((System.currentTimeMillis() % 10000).toInt(), builder.build())
        } catch (_: SecurityException) {
        }
    }

    fun notifyRiskBreach(reason: String) {
        try {
            val builder = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_error)
                .setContentTitle("🚨 Risk Limit Constraint Triggered")
                .setContentText(reason)
                .setStyle(NotificationCompat.BigTextStyle().bigText(reason))
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setContentIntent(getPendingIntent())
                .setAutoCancel(true)

            val notificationManager = NotificationManagerCompat.from(context)
            notificationManager.notify(9999, builder.build())
        } catch (_: SecurityException) {
        }
    }
}
