package kr.co.farmerflood.trigger.provider;
import kr.co.farmerflood.trigger.config.AppProperties; import kr.co.farmerflood.trigger.domain.RiskLevel;
public final class RiskClassifier { private RiskClassifier(){} public static RiskLevel classify(double l,AppProperties.Thresholds t){if(l>=t.getSerious())return RiskLevel.SERIOUS;if(l>=t.getAlert())return RiskLevel.ALERT;if(l>=t.getCaution())return RiskLevel.CAUTION;if(l>=t.getAttention())return RiskLevel.ATTENTION;return RiskLevel.NORMAL;} }
