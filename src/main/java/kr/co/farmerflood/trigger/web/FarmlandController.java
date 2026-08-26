package kr.co.farmerflood.trigger.web;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;
import kr.co.farmerflood.trigger.service.FarmlandService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api")
public class FarmlandController {
    private final FarmlandService service;
    public FarmlandController(FarmlandService service){this.service=service;}
    @PostMapping("/users") @ResponseStatus(HttpStatus.CREATED)
    public FarmlandService.UserView createUser(@Valid @RequestBody CreateUser request){return service.createUser(request.email(),request.name());}
    @PostMapping("/farmlands") @ResponseStatus(HttpStatus.CREATED)
    public FarmlandService.FarmlandView register(@Valid @RequestBody RegisterFarmland request){return service.register(new FarmlandService.RegisterFarmland(request.userId(),request.name(),request.address(),request.province(),request.district(),request.locality(),request.sourceParcelId(),request.pnu(),request.areaSquareMeters(),request.latitude(),request.longitude(),request.boundaryGeoJson(),request.regionId()));}
    @GetMapping("/farmlands") public List<FarmlandService.FarmlandView> farmlands(@RequestParam(required=false)String userId){return userId==null?service.all():service.byUser(userId);}
    @PostMapping("/farmlands/{id}/monitoring-stations/relink") public FarmlandService.FarmlandView relink(@PathVariable String id){return service.relink(id);}
    public record CreateUser(@Email @NotBlank String email,@NotBlank String name){}
    public record RegisterFarmland(@NotBlank String userId,@NotBlank String name,@NotBlank String address,String province,String district,String locality,String sourceParcelId,String pnu,Double areaSquareMeters,@DecimalMin("33.0") @DecimalMax("39.0") double latitude,@DecimalMin("124.0") @DecimalMax("132.0") double longitude,String boundaryGeoJson,String regionId){}
}
