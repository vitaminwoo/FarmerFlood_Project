package kr.co.farmerflood.trigger.provider;
public final class KmaGridConverter {
 private KmaGridConverter(){}
 public static Grid from(double lat,double lon){double re=6371.00877/5.0,slat1=Math.toRadians(30),slat2=Math.toRadians(60),olon=126,olat=38,xo=43,yo=136;double sn=Math.log(Math.cos(slat1)/Math.cos(slat2))/Math.log(Math.tan(Math.PI*.25+slat2*.5)/Math.tan(Math.PI*.25+slat1*.5));double sf=Math.pow(Math.tan(Math.PI*.25+slat1*.5),sn)*Math.cos(slat1)/sn;double ro=re*sf/Math.pow(Math.tan(Math.PI*.25+Math.toRadians(olat)*.5),sn);double ra=re*sf/Math.pow(Math.tan(Math.PI*.25+Math.toRadians(lat)*.5),sn);double theta=Math.toRadians(lon-olon);if(theta>Math.PI)theta-=2*Math.PI;if(theta<-Math.PI)theta+=2*Math.PI;theta*=sn;return new Grid((int)Math.floor(ra*Math.sin(theta)+xo+1.5),(int)Math.floor(ro-ra*Math.cos(theta)+yo+1.5));}
 public record Grid(int nx,int ny){}
}
