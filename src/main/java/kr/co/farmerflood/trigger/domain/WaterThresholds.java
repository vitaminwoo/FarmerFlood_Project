package kr.co.farmerflood.trigger.domain;
public record WaterThresholds(Double attention,Double caution,Double alert,Double serious){
    public boolean complete(){return attention!=null&&caution!=null&&alert!=null&&serious!=null;}
}
