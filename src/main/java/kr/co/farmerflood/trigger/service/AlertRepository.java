package kr.co.farmerflood.trigger.service;

import java.util.List;
import kr.co.farmerflood.trigger.domain.*;
import kr.co.farmerflood.trigger.persistence.*;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class AlertRepository {
    private final AlertJpaRepository repository;
    public AlertRepository(AlertJpaRepository repository){this.repository=repository;}
    @Transactional public void save(AlertEvent a){AlertEntity e=new AlertEntity();e.id=a.id();e.locationId=a.locationId();e.locationName=a.locationName();e.stationCode=a.stationCode();e.stationName=a.stationName();e.address=a.address();e.nx=a.nx();e.ny=a.ny();e.waterLevelMeters=a.waterLevelMeters();e.riskLevel=a.riskLevel().name();e.forecastRainfallMm=a.forecastRainfallMm();e.rainfallThresholdMm=a.rainfallThresholdMm();e.triggeredAt=a.triggeredAt();e.userId=a.userId();e.farmlandId=a.farmlandId();e.productionRequested=a.productionRequested();e.productionDecision=a.productionDecision();repository.save(e);}
    public AlertEvent find(String id){return repository.findById(id).map(this::domain).orElse(null);}
    public List<AlertEvent> findAll(){return repository.findAllByOrderByTriggeredAtDesc().stream().map(this::domain).toList();}
    private AlertEvent domain(AlertEntity e){boolean requested=Boolean.TRUE.equals(e.productionRequested);String decision=e.productionDecision!=null?e.productionDecision:(requested?"영상 제작 후 송신":"기존 트리거 기록 · 영상 제작 하지 않음");return new AlertEvent(e.id,e.locationId,e.locationName,e.stationCode,e.stationName,e.address,e.nx,e.ny,e.waterLevelMeters,RiskLevel.valueOf(e.riskLevel),e.forecastRainfallMm,e.rainfallThresholdMm,e.triggeredAt,e.userId,e.farmlandId,requested,decision);}
}
