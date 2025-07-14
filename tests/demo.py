from confull import Config

# 1) 加密 + 去抖保存（100 ms），支持 toml
cfg = Config({'token': 'abc'}, file='secure.toml', pwd='secret', debounce_ms=100)
cfg.write('log.level', 'INFO')
print(cfg)