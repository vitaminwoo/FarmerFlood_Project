package kr.co.farmerflood.trigger.provider.live;
public class ProviderException extends RuntimeException { public ProviderException(String provider,String message){super(provider+": "+message);} }
