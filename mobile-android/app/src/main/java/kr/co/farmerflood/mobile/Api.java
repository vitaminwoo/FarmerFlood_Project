package kr.co.farmerflood.mobile;

import java.io.*;import java.net.*;import java.nio.charset.StandardCharsets;import org.json.*;

final class Api {
    static JSONObject get(String path,String token)throws Exception{return request("GET",path,null,token);}
    static JSONObject post(String path,JSONObject body,String token)throws Exception{return request("POST",path,body,token);}
    static void delete(String path,String token)throws Exception{raw("DELETE",path,null,token);}
    static JSONArray getArray(String path,String token)throws Exception{return new JSONArray(raw("GET",path,null,token));}
    private static JSONObject request(String method,String path,JSONObject body,String token)throws Exception{
        String text=raw(method,path,body,token);return text.isBlank()?new JSONObject():new JSONObject(text);
    }
    private static String raw(String method,String path,JSONObject body,String token)throws Exception{
        HttpURLConnection c=(HttpURLConnection)new URL(BuildConfig.API_BASE_URL+path).openConnection();c.setRequestMethod(method);c.setConnectTimeout(5000);c.setReadTimeout(60000);c.setRequestProperty("Accept","application/json");if(token!=null)c.setRequestProperty("Authorization","Bearer "+token);
        if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");try(OutputStream out=c.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}}
        int status=c.getResponseCode();InputStream stream=status>=400?c.getErrorStream():c.getInputStream();String text=stream==null?"":new String(stream.readAllBytes(),StandardCharsets.UTF_8);if(status>=400){try{throw new IOException(new JSONObject(text).optString("message",text));}catch(JSONException e){throw new IOException(text);}}return text;
    }
}
