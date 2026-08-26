package kr.co.farmerflood.mobile;

import android.app.*;import android.content.*;import android.os.*;import org.json.*;

public class NotificationRelayService extends Service {
    static final String CHANNEL_STATUS="flood_connection",CHANNEL_ALERT="flood_alerts";private volatile boolean running;
    @Override public void onCreate(){super.onCreate();createChannels();startForeground(10,statusNotification());running=true;new Thread(this::loop,"mobile-alert-relay").start();}
    @Override public int onStartCommand(Intent i,int flags,int id){return START_STICKY;}
    @Override public void onDestroy(){running=false;super.onDestroy();}
    @Override public android.os.IBinder onBind(Intent i){return null;}
    private void loop(){while(running){try{String token=getSharedPreferences("session",MODE_PRIVATE).getString("token",null);if(token==null){stopSelf();return;}checkArray(Api.getArray("/api/mobile/notifications",token),token);}catch(Exception ignored){}try{Thread.sleep(3000);}catch(InterruptedException e){return;}}}
    private void checkArray(JSONArray items,String token)throws Exception{
        if(items==null)return;
        var prefs=getSharedPreferences("session",MODE_PRIVATE);
        String last=prefs.getString("lastNotificationId","");
        boolean initialized=prefs.getBoolean("notificationBaselineInitialized",false);

        // 첫 연결에서는 서버의 과거 알림을 기준점으로만 저장한다. 이후에는 최신순 목록에서
        // 마지막으로 처리한 ID보다 앞에 추가된 항목만 새 시스템 알림으로 표시한다.
        if(!initialized){
            String baseline=items.length()==0?"":items.getJSONObject(0).getString("id");
            prefs.edit().putBoolean("notificationBaselineInitialized",true).putString("lastNotificationId",baseline).commit();
            return;
        }
        if(items.length()==0)return;
        String newest=items.getJSONObject(0).getString("id");
        if(newest.equals(last))return;

        int previousIndex=-1;
        if(!last.isBlank())for(int i=0;i<items.length();i++)if(last.equals(items.getJSONObject(i).getString("id"))){previousIndex=i;break;}
        int newCount=last.isBlank()?items.length():previousIndex;
        if(previousIndex<0&&!last.isBlank())newCount=1; // 목록 보관 범위 밖이면 최신 한 건만 안전하게 알린다.

        // 앱이 중간에 종료되더라도 같은 항목을 무한 재발송하지 않도록 표시 전에 체크포인트를 저장한다.
        prefs.edit().putString("lastNotificationId",newest).commit();
        for(int i=newCount-1;i>=0;i--)showAlert(items.getJSONObject(i));
    }
    private void showAlert(JSONObject n)throws Exception{Intent open=new Intent(this,MainActivity.class).putExtra("mediaUrl",n.getString("mediaUrl")).putExtra("notificationId",n.getString("id")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TOP);PendingIntent pi=PendingIntent.getActivity(this,n.getString("id").hashCode(),open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);Notification notification=new Notification.Builder(this,CHANNEL_ALERT).setSmallIcon(android.R.drawable.stat_sys_warning).setContentTitle(n.getString("title")).setContentText(n.getString("body")).setStyle(new Notification.BigTextStyle().bigText(n.getString("body"))).setAutoCancel(true).setPriority(Notification.PRIORITY_HIGH).setContentIntent(pi).build();getSystemService(NotificationManager.class).notify(n.getString("id").hashCode(),notification);sendBroadcast(new Intent("kr.co.farmerflood.mobile.NEW_ALERT").setPackage(getPackageName()));}
    private Notification statusNotification(){return new Notification.Builder(this,CHANNEL_STATUS).setSmallIcon(android.R.drawable.stat_notify_sync).setContentTitle("농경지 홍수 알림 연결 중").setContentText("완성된 경고 영상을 기다리고 있습니다.").setOngoing(true).build();}
    private void createChannels(){NotificationManager m=getSystemService(NotificationManager.class);m.createNotificationChannel(new NotificationChannel(CHANNEL_STATUS,"알림 연결 상태",NotificationManager.IMPORTANCE_LOW));m.createNotificationChannel(new NotificationChannel(CHANNEL_ALERT,"침수 경고",NotificationManager.IMPORTANCE_HIGH));}
}
