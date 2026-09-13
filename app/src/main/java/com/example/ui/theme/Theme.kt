package com.example.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val TerminalDarkColorScheme = darkColorScheme(
    primary = NeonCyan,
    onPrimary = Color.Black,
    primaryContainer = CyanAlpha10,
    onPrimaryContainer = NeonCyan,
    secondary = NeonEmerald,
    onSecondary = Color.Black,
    secondaryContainer = GreenAlpha10,
    onSecondaryContainer = NeonEmerald,
    tertiary = WarningAmber,
    onTertiary = Color.Black,
    background = TerminalBackground,
    onBackground = TextPrimary,
    surface = TerminalSurface,
    onSurface = TextPrimary,
    surfaceVariant = TerminalCard,
    onSurfaceVariant = TextSecondary,
    outline = TerminalCardBorder,
    error = DangerRed,
    onError = Color.White,
)

@Composable
fun DerivBotTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = TerminalDarkColorScheme,
        typography = Typography,
        content = content
    )
}
