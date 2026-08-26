package kr.co.farmerflood.trigger.provider.live;
import java.util.regex.*;
public final class KmaRainfallParser { private static final Pattern N=Pattern.compile("([0-9]+(?:\\.[0-9]+)?)"); private KmaRainfallParser(){} public static double millimeters(String raw){if(raw==null||raw.isBlank()||raw.contains("강수없음"))return 0;Matcher m=N.matcher(raw.replace(",",""));if(!m.find())return 0;double first=Double.parseDouble(m.group(1));if(raw.contains("미만"))return first/2;if((raw.contains("~")||raw.contains("∼"))&&m.find())return(first+Double.parseDouble(m.group(1)))/2;return first;} }
