package kr.co.farmerflood.trigger.service;

import java.util.*;
import kr.co.farmerflood.trigger.domain.RiskLevel;
import kr.co.farmerflood.trigger.persistence.*;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class TriggerStateRepository {
    private final TriggerStateJpaRepository repository;
    public TriggerStateRepository(TriggerStateJpaRepository repository){this.repository=repository;}
    @Transactional public TriggerState save(TriggerState state){TriggerStateEntity e=new TriggerStateEntity();e.locationId=state.locationId();e.phase=state.phase().name();e.riskLevel=state.riskLevel().name();e.waterLevelMeters=state.waterLevelMeters();e.forecastRainfallMm=state.forecastRainfallMm();e.alertId=state.alertId();e.lastError=state.lastError();e.updatedAt=state.updatedAt();repository.save(e);return state;}
    public Optional<TriggerState> find(String id){return repository.findById(id).map(this::domain);}
    public List<TriggerState> findAll(){return repository.findAll().stream().map(this::domain).toList();}
    private TriggerState domain(TriggerStateEntity e){return new TriggerState(e.locationId,TriggerState.Phase.valueOf(e.phase),RiskLevel.valueOf(e.riskLevel),e.waterLevelMeters,e.forecastRainfallMm,e.alertId,e.lastError,e.updatedAt);}
}
