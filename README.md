<h1 align="center">Peeper-Board-Generator</h1>
<div align="center">
  <strong>免费，开源的 OJ 榜单生成器</strong><br>
</div><br>

<div align="center">
  <a href="https://github.com/qwedc001/Peeper-Board-Generator/blob/master/requirements.txt"><img alt="Supported Python Version" src="https://img.shields.io/badge/Python-3.10+-teal?style=flat-square"></a>
  <a href="https://github.com/qwedc001/Peeper-Board-Generator/commits"><img alt="GitHub Last Commit" src="https://img.shields.io/github/last-commit/qwedc001/Peeper-Board-Generator?style=flat-square"></a>
  <a href="https://github.com/qwedc001/Peeper-Board-Generator/releases/latest"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/qwedc001/Peeper-Board-Generator?style=flat-square&label=Peeper-Board-Generator"></a>
  <a href="https://github.com/qwedc001/Peeper-Board-Generator/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/qwedc001/Peeper-Board-Generator?style=flat-square"></a>
  <a href="https://github.com/qwedc001/Peeper-Board-Generator/commits"><img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/y/qwedc001/Peeper-Board-Generator?style=flat-square"></a>
</div>


特点：

- **高度模块化**: 允许用户自定义模块（分为 OJ 爬取模块和榜单生成模块），方便用户开发更多的榜单主题和接入更多 OJ。
- **灵活**: 支持命令行调用程序直接生图 / QQ Bot 调用(coming soon)
- **内置大量单元测试**: 方便用户二次开发时对开发模块进行快速测试

用户群：[995417734](https://qm.qq.com/q/Bt45INhxB0)

欢迎接入更多的 OJ 以及编写更多的榜单样式，欢迎提交 issue 和 pr。

## 支持的 OJ
- [x] Hydro
- [ ] Codeforces
- [ ] Atcoder

## TODO
- [ ] 进一步完善 theme / misc 的文件结构
- [ ] 完善多 OJ 支持 和多 theme 支持
- [ ] 完善 QQ Bot 调用部分

## 使用方法
1. 安装依赖
```bash
uv sync --frozen
```
2. 编写配置文件

生成器支持多榜单导出，请参照 `config_example.json` 编写配置文件，将其保存为 `config.json`。

> [!WARNING]
> 目前 `config_example.json` 内包含 Hydro 榜单 和 Codeforces 榜单 的配置文件示例，请删去未填写完整的榜单配置，或者使用 `--id` 指定想要生成的榜单。

3. 运行程序
```bash
python main.py --help

usage: main.py [-h] (--version | --full | --now | --query_uid QUERY_UID | --query_name QUERY_NAME) [--output OUTPUT] [--verdict VERDICT] [--id ID] [--separate_cols]
               [--performance_statistics]

Peeper-Board-Generator OJ榜单图片生成器

options:
  -h, --help            show this help message and exit
  --version             版本号信息
  --full                生成昨日榜单
  --now                 生成从今日0点到当前时间的榜单
  --query_uid QUERY_UID
                        根据 uid 查询指定用户的信息
  --query_name QUERY_NAME
                        根据用户名查询指定用户的信息
  --output OUTPUT       指定生成图片的路径 (包含文件名)
  --verdict VERDICT     指定榜单对应verdict (使用简写)
  --id ID               生成指定 id 的榜单(留空则生成全部榜单)
  --separate_cols       是否启用分栏特性
  --performance_statistics
                        性能测试
  --config CONFIG       指定配置文件路径
  --verbose             显示更详细的日志
```

## 样例图片

> [!TIP]
> - 图片中 "YOUR Online Judge" 字样可在 `configs.json` 中的 `board_name` 字段更改；
> - 底部 Tips 分栏随版本更新，可在 [此 issue](https://github.com/qwedc001/Peeper-Board-Generator/issues/41) 下投稿。

<details open>
<summary><h3>昨日榜单 (<code>--full</code>)</h3></summary>
<img src="example_full.png" alt="昨日榜单" />
</details>

<details>
<summary><h3>从今日0点到当前时间的榜单 (<code>--now</code>)</h3></summary>
<img src="example_now.png" alt="今日榜单" />
</details>

<details>
<summary><h3>从今日0点到当前时间的 Wrong Answer 榜单 (<code>--now --verdict WA</code>)</h3></summary>
<img src="example_verdict_wa.png" alt="今日特定 verdict 榜单" />
</details>

<details>
<summary><h3>数据较多时可开启分栏 (<code>... --separate_cols</code>)</h3></summary>
<img src="example_full_multi.png" alt="开启分栏的昨日榜单" />
</details>


## 致谢

**Dev Team**: FJNU-[Floating-Ocean](https://github.com/Floating-Ocean)，QLU-[qwedc001](https://github.com/qwedc001)

**贡献者**: QLU-[Euphria](https://github.com/Euphria)
