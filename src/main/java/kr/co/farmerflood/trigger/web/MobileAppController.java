package kr.co.farmerflood.trigger.web;
import jakarta.validation.Valid;import jakarta.validation.constraints.*;import java.util.List;import kr.co.farmerflood.trigger.service.*;import org.springframework.http.HttpStatus;import org.springframework.web.bind.annotation.*;import reactor.core.publisher.Mono;import reactor.core.scheduler.Schedulers;
@RestController @RequestMapping("/api/mobile") public class MobileAppController {
 private final MobileAppService app;private final ChungbukRegionService regions;public MobileAppController(MobileAppService a,ChungbukRegionService r){app=a;regions=r;}
 @GetMapping("/regions")public ChungbukRegionService.RegionView regions(){return regions.view();}
 @PostMapping("/auth/signup")@ResponseStatus(HttpStatus.CREATED)public Mono<MobileAppService.SessionView> signup(@Valid @RequestBody Signup r){return blocking(()->app.signup(r.name(),r.phone(),r.district(),r.locality(),r.parcelId()));}
 @PostMapping("/auth/login")public Mono<MobileAppService.SessionView> login(@Valid @RequestBody Login r){return blocking(()->app.login(r.name(),r.phone()));}
 @PostMapping("/auth/guardian/signup")@ResponseStatus(HttpStatus.CREATED)public Mono<MobileAppService.SessionView> guardianSignup(@Valid @RequestBody GuardianAuth r){return blocking(()->app.guardianSignup(r.guardianName(),r.farmerName(),r.farmerPhone()));}
 @PostMapping("/auth/guardian/login")public Mono<MobileAppService.SessionView> guardianLogin(@Valid @RequestBody GuardianAuth r){return blocking(()->app.guardianLogin(r.guardianName(),r.farmerName(),r.farmerPhone()));}
 @GetMapping("/me")public Mono<MobileAppService.SessionView> me(@RequestHeader("Authorization")String auth){return blocking(()->app.me(token(auth)));}
 @GetMapping("/notifications")public Mono<List<MobileAppService.NotificationView>> notifications(@RequestHeader("Authorization")String auth){return blocking(()->app.notifications(token(auth)));}
 @PostMapping("/notifications/{id}/read")@ResponseStatus(HttpStatus.NO_CONTENT)public Mono<Void> read(@RequestHeader("Authorization")String auth,@PathVariable String id){return blocking(()->{app.markRead(token(auth),id);return true;}).then();}
 @DeleteMapping("/me")@ResponseStatus(HttpStatus.NO_CONTENT)public Mono<Void> withdraw(@RequestHeader("Authorization")String auth){return blocking(()->{app.withdraw(token(auth));return true;}).then();}
 private <T> Mono<T> blocking(java.util.concurrent.Callable<T> task){return Mono.fromCallable(task).subscribeOn(Schedulers.boundedElastic());}
 private String token(String value){if(value==null||!value.startsWith("Bearer "))throw new SecurityException("로그인이 필요합니다.");return value.substring(7);}
 public record Signup(@NotBlank String name,@Pattern(regexp="[0-9 -]{10,15}")String phone,@NotBlank String district,@NotBlank String locality,@NotBlank String parcelId){}
 public record Login(@NotBlank String name,@Pattern(regexp="[0-9 -]{10,15}")String phone){}
 public record GuardianAuth(@NotBlank String guardianName,@NotBlank String farmerName,@Pattern(regexp="[0-9 -]{10,15}")String farmerPhone){}
}
