# bilibili_dm_plugin

适配于[ictye-live-Danmku](https://github.com/northgreen/ictye-live-dm)的一个示范性插件，用于简单的获取哔哩哔哩直播的弹幕

通过访问进行连接
```
http://127.0.0.1:12345/index?&broom={roomid}
```

也就是传递一个get参数（`roomid`），注意要跳过第一个参数，也就是写成`?&`的形式