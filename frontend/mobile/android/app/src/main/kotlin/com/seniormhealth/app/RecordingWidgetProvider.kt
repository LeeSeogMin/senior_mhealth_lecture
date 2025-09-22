package com.seniormhealth.app

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import android.util.Log

class RecordingWidgetProvider : AppWidgetProvider() {

    companion object {
        private const val TAG = "RecordingWidgetProvider"
        const val ACTION_START_RECORDING = "com.seniormhealth.app.START_RECORDING"
        
        // 위젯 업데이트 메소드
        fun updateWidget(context: Context, appWidgetManager: AppWidgetManager, appWidgetId: Int) {
            Log.d(TAG, "updateWidget 호출됨 - widgetId: $appWidgetId")
            
            // 위젯 레이아웃 생성
            val views = RemoteViews(context.packageName, R.layout.widget_recording_layout)
            
            // 녹음 시작 버튼 클릭 시 Intent 설정
            val startRecordingIntent = Intent(context, RecordingWidgetProvider::class.java).apply {
                action = ACTION_START_RECORDING
                putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, appWidgetId)
            }
            
            val pendingIntent = PendingIntent.getBroadcast(
                context, 
                appWidgetId,
                startRecordingIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            
            views.setOnClickPendingIntent(R.id.btn_start_recording, pendingIntent)
            
            // 위젯 업데이트
            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        Log.d(TAG, "onUpdate 호출됨 - widgets: ${appWidgetIds.size}개")
        
        // 모든 위젯 인스턴스 업데이트
        for (appWidgetId in appWidgetIds) {
            updateWidget(context, appWidgetManager, appWidgetId)
        }
    }

    override fun onEnabled(context: Context) {
        Log.d(TAG, "첫 번째 위젯이 추가됨")
        super.onEnabled(context)
    }

    override fun onDisabled(context: Context) {
        Log.d(TAG, "마지막 위젯이 제거됨")
        super.onDisabled(context)
    }

    override fun onReceive(context: Context, intent: Intent) {
        Log.d(TAG, "onReceive - action: ${intent.action}")
        
        when (intent.action) {
            ACTION_START_RECORDING -> {
                Log.d(TAG, "🎤 녹음 시작 요청 받음!")
                handleStartRecording(context)
            }
            else -> {
                super.onReceive(context, intent)
            }
        }
    }

    private fun handleStartRecording(context: Context) {
        Log.d(TAG, "handleStartRecording 실행")
        
        try {
            // MainActivity로 인텐트 전송하여 앱 실행 및 녹음 시작
            val mainActivityIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("start_recording", true)
            }
            
            context.startActivity(mainActivityIntent)
            Log.d(TAG, "✅ MainActivity로 녹음 시작 요청 전송됨")
            
        } catch (e: Exception) {
            Log.e(TAG, "❌ 녹음 시작 실패: ${e.message}", e)
        }
    }
} 