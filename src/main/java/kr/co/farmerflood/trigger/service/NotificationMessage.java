package kr.co.farmerflood.trigger.service; import java.time.Instant; public record NotificationMessage(String alertId,String title,String body,String mediaUrl,Instant sentAt){}
