package kr.co.farmerflood.trigger.service; import org.springframework.stereotype.Component; import reactor.core.publisher.*;
@Component public class WebNotificationGateway {private final Sinks.Many<NotificationMessage> sink=Sinks.many().multicast().directBestEffort();public void send(NotificationMessage m){sink.tryEmitNext(m);}public Flux<NotificationMessage> stream(){return sink.asFlux();}}
