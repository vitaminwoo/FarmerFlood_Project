package kr.co.farmerflood.trigger.domain;
public enum RiskLevel {
    NORMAL("현재",0), ATTENTION("관심",1), CAUTION("주의",2), ALERT("경계",3), SERIOUS("심각",4);
    private final String label; private final int rank;
    RiskLevel(String label,int rank){this.label=label;this.rank=rank;}
    public String label(){return label;} public boolean atLeast(RiskLevel other){return rank>=other.rank;}
}
