# 将航空日报聚合页发布到公网（自定义域名 wittywiz.cc）

本项目的 `web/index.html` 是纯静态页面，从 Supabase 拉取数据，适合用 **GitHub Pages** 免费托管，再绑定你在阿里云购买的域名 **wittywiz.cc**。

---

## 国内访问说明（重要）

- **仅用阿里云解析**：只影响「域名解析」在国内的稳定与速度，**不能保证国内一定能正常打开网站**。因为页面内容仍从 **GitHub Pages**（境外）拉取，国内访问 GitHub 有时会慢或不稳定。
- **若需要国内稳定、公开访问**：应把**网站内容放到国内**，例如 **阿里云 OSS + CDN**，域名用阿里云解析指到阿里云。这样解析和内容都在国内，国内访问才可靠。具体做法见文末「国内访问方案：阿里云 OSS + CDN」。

---

## 一、用 GitHub Pages 托管（免费）

### 1. 开启 GitHub Pages 并选用 Actions 部署

1. 打开仓库：<https://github.com/xiaomaupup/Global-AeroPulse>
2. 点击 **Settings** → 左侧 **Pages**
3. 在 **Build and deployment** 里：
   - **Source** 选 **GitHub Actions**

保存后，仓库里已有 workflow：**Deploy News Page to GitHub Pages**。每次你往 `main` 分支推送且改动了 `web/` 下的文件时，会自动把 `web/` 发布到 Pages。

### 2. 手动触发一次部署（可选）

- 打开 **Actions** → 选择 **Deploy News Page to GitHub Pages** → **Run workflow** → 选分支 **main** → Run
- 跑完后，站点会出现在：`https://xiaomaupup.github.io/Global-AeroPulse/`

此时已经可以公网访问，只是地址还是 GitHub 的。

---

## 二、绑定你的域名 wittywiz.cc

建议用**子域名**绑定日报站，例如 **news.wittywiz.cc**，这样主站 `wittywiz.cc` 仍可作它用。

---

### 本项目专用：Cloudflare 完整配置步骤（推荐按此操作）

若你打算用 **Cloudflare** 做解析（和另一个项目一致），按下面顺序做即可。

#### 第一步：在 Cloudflare 里「添加站点」（若列表里还没有 wittywiz.cc）

1. 打开 **https://dash.cloudflare.com/** 并登录。
2. 点击 **Add a site**（添加站点），输入 **wittywiz.cc**，继续。
3. 选择 **Free** 计划，继续。
4. Cloudflare 会扫描该域名的现有解析记录（可能为空），扫描完后点 **Continue**。
5. 接下来会看到 **Update your nameservers** 页面，给出两个 NS 地址，例如：
   - `xxx.ns.cloudflare.com`
   - `yyy.ns.cloudflare.com`  
   **先不要关这个页面**，记下这两个地址（或保持页面开着）。

#### 第二步：把域名的 DNS 服务器改成 Cloudflare 的

1. 打开你**购买域名**的地方（例如阿里云域名控制台 **https://dc.console.aliyun.com/**）。
2. 找到域名 **wittywiz.cc** → 点击 **管理** → 找到 **DNS 修改** / **修改 DNS 服务器**。
3. 把原来的 DNS 服务器**改成**第一步里 Cloudflare 给的那两个（例如 `xxx.ns.cloudflare.com` 和 `yyy.ns.cloudflare.com`），保存。
4. 等待几分钟到几小时生效。生效后，在 Cloudflare 里该站点状态会变成 **Active**（若仍是 Pending，多等一会儿或检查 NS 是否填对）。

#### 第三步：在 Cloudflare 里添加 CNAME（把 news.wittywiz.cc 指到 GitHub Pages）

1. 在 [Cloudflare Dashboard](https://dash.cloudflare.com/) 左侧选中域名 **wittywiz.cc**。
2. 左侧菜单点 **DNS** → **Records**（记录）。
3. 点 **Add record**（添加记录），按下面填写：
   - **Type**：选 **CNAME**
   - **Name**：填 **news**（只填英文 `news`，不要填 `news.wittywiz.cc`）
   - **Target**：填 **xiaomaupup.github.io**
   - **Proxy status**：选 **DNS only**（灰色云朵），不要开橙色云朵（否则可能和 GitHub Pages 校验冲突）
   - **TTL**：保持 Auto 即可
4. 点 **Save** 保存。

#### 第四步：在 GitHub 里填自定义域名

1. 打开仓库 **https://github.com/xiaomaupup/Global-AeroPulse** → **Settings** → 左侧 **Pages**。
2. 在 **Custom domain** 输入框里填：**news.wittywiz.cc**，点 **Save**。
3. 若提示 DNS 未通过，等 1～5 分钟再点一次 Save，或先执行下面「第五步」自检后再保存。
4. 证书生效后，可勾选 **Enforce HTTPS**。

#### 第五步：自检（可选）

在终端执行：

```bash
dig news.wittywiz.cc CNAME
```

若 **ANSWER SECTION** 里出现 `news.wittywiz.cc. ... CNAME xiaomaupup.github.io.`，说明解析已生效。然后打开 **https://news.wittywiz.cc** 应能看到航空日报聚合页。

---

### 若你已确定域名在 Cloudflare，只需加一条 CNAME

若 **wittywiz.cc** 早已在 Cloudflare 里且状态为 Active，只需做上面的 **第三步 + 第四步**：在 Cloudflare 加一条 CNAME（name=news, target=xiaomaupup.github.io, DNS only），再到 GitHub Pages 填 Custom domain。

### 若域名在阿里云云解析（不用 Cloudflare）

1. 登录 [阿里云云解析控制台](https://dns.console.aliyun.com/)，找到 **wittywiz.cc** → **解析设置**。
2. **添加记录**：类型 `CNAME`，主机记录 `news`，记录值 `xiaomaupup.github.io`，TTL 10 分钟。
3. 保存后同上，用 `dig` 确认再在 GitHub 保存 Custom domain。

#### 若在 Cloudflare 里看不到该域名（NS 却是 Cloudflare）

说明域名可能在其他 Cloudflare 账号下，或由注册商预置。**可改为用阿里云解析**（域名在阿里云购买时推荐）：

1. **在阿里云云解析里先添加域名**  
   登录 [云解析 DNS](https://dns.console.aliyun.com/) → 权威解析 → 添加域名 → 输入 `wittywiz.cc`，添加后记下分配的 **DNS 服务器**（如 `vip1.alidns.com`、`vip2.alidns.com`，以控制台显示为准）。

2. **把域名的 NS 改到阿里云**  
   登录 [阿里云域名控制台](https://dc.console.aliyun.com/) → 域名列表 → 找到 **wittywiz.cc** → 点击 **管理** → **DNS 修改** → 选择「使用 阿里云 DNS」或「自定义 DNS」，填入上一步的 NS 地址 → 保存。（生效通常几分钟到几小时。）

3. **在云解析里添加 CNAME**  
   回到 [云解析 DNS](https://dns.console.aliyun.com/) → 选择 **wittywiz.cc** → 解析设置 → 添加记录：类型 `CNAME`，主机记录 `news`，记录值 `xiaomaupup.github.io`，TTL 10 分钟 → 保存。

4. 等 5～30 分钟后执行 `dig news.wittywiz.cc CNAME` 确认解析到 `xiaomaupup.github.io`，再在 GitHub Pages 里保存 Custom domain。

### 3. 等待生效

- DNS 生效一般 5–30 分钟，有时更久
- GitHub 会为 `news.wittywiz.cc` 自动申请 HTTPS 证书，生效后可在 Pages 设置里勾选 **Enforce HTTPS**

完成后，用浏览器打开 **https://news.wittywiz.cc** 即可访问航空日报聚合页。

---

## 三、若要用根域名 wittywiz.cc 访问

若希望直接使用 `https://wittywiz.cc` 作为日报站：

1. 在 GitHub Pages 的 **Custom domain** 填：`wittywiz.cc`
2. 在阿里云 DNS 添加：
   - 类型 **CNAME**，主机记录 **@**，记录值 **xiaomaupup.github.io**

注意：根域名绑定后，该域名就只能指向这个 Pages 站，不能再同时做其它网站（除非用 Nginx 等反向代理）。用子域名 `news.wittywiz.cc` 更灵活。

---

## 四、页面里用到的 Supabase

- 当前 `web/index.html` 里写的是 Supabase 的 **anon（可公开）key**，前端直接请求 Supabase，**可以**放在公网。
- 请勿把 **service_role key** 写进前端；若以后要改 API 或 key，只需改 `web/index.html` 里 `SUPABASE_URL` / `SUPABASE_ANON_KEY`，再推一次代码即可重新部署。

---

## 五、简要检查清单

| 步骤 | 说明 |
|------|------|
| 1 | 仓库 Settings → Pages → Source 选 **GitHub Actions** |
| 2 | 推送包含 `web/` 的提交，或手动 Run workflow **Deploy News Page to GitHub Pages** |
| 3 | 访问 `https://xiaomaupup.github.io/Global-AeroPulse/` 确认能打开 |
| 4 | Settings → Pages → Custom domain 填 **news.wittywiz.cc**（或 wittywiz.cc） |
| 5 | 阿里云 DNS 添加 CNAME：news → xiaomaupup.github.io |
| 6 | 等待 DNS + HTTPS 生效后访问 **https://news.wittywiz.cc** |

如有报错，可到 **Actions** 里看 **Deploy News Page to GitHub Pages** 的日志排查。

---

## 六、常见报错：InvalidDNSError / "improperly configured"

若 GitHub 提示 **Domain's DNS record could not be retrieved (InvalidDNSError)**，按下面逐项检查：

1. **阿里云「主机记录」只填 `news`**  
   不能填 `news.wittywiz.cc`，否则会变成 `news.wittywiz.cc.wittywiz.cc`。

2. **「记录值」只填 `xiaomaupup.github.io`**  
   不要带 `https://`、不要带结尾 `/`、不要有多余空格。

3. **域名实际在用哪家 DNS**  
   用 `dig news.wittywiz.cc` 看返回里的 **AUTHORITY SECTION**：若出现 `cloudflare.com` 说明是 **Cloudflare** 解析，要在 Cloudflare 控制台添加 CNAME；若是阿里云 NS 才在阿里云添加。域名在谁家解析，就要在谁家加记录。

4. **等 DNS 生效后再在 GitHub 保存**  
   添加/修改记录后等 5–30 分钟，在终端执行：  
   `dig news.wittywiz.cc CNAME`  
   或使用 [chinaz DNS 查询](https://tool.chinaz.com/dns?host=news.wittywiz.cc) 看是否返回 `xiaomaupup.github.io`。确认能解析后再在 GitHub Pages 里保存 Custom domain。

---

## 七、国内访问方案：阿里云 OSS + CDN（可选）

若需要**中国国内稳定、公开访问**，建议把同一套静态页面放到**阿里云 OSS**（并可选开通 CDN），用阿里云解析把 `news.wittywiz.cc` 指到阿里云。这样解析和内容都在国内，国内访问才可靠。

**前提**：在中国大陆对自定义域名使用 OSS 国内节点或 CDN 国内节点，通常要求该域名已完成 **ICP 备案**（在阿里云备案或接入备案）。若 `wittywiz.cc` 尚未备案，需先在阿里云完成备案后再按下面操作。

**简要步骤**（具体以阿里云控制台为准）：

1. **创建 OSS 存储桶**  
   登录 [对象存储 OSS](https://oss.console.aliyun.com/) → 创建 Bucket，地域选国内（如华东1），读写权限选**公共读**。

2. **开启静态页面托管**  
   进入该 Bucket → 基础设置 → 静态页面托管 → 设置默认首页为 `index.html`。

3. **上传网站文件**  
   把本仓库 `web/` 目录下的 `index.html`、`CNAME`（可选，OSS 绑定自定义域名时不依赖此文件）等上传到 Bucket 根目录。

4. **绑定自定义域名并开启 HTTPS**  
   在 Bucket 的「传输管理」或「域名管理」中绑定 `news.wittywiz.cc`，并开启 HTTPS（阿里云可申请免费证书）。若使用 **CDN**，则在 CDN 控制台添加域名、源站选择该 OSS Bucket，再在 CDN 上绑定 `news.wittywiz.cc` 和证书，可加速全国访问。

5. **阿里云解析**  
   在 [云解析 DNS](https://dns.console.aliyun.com/) 中，为 `wittywiz.cc` 添加记录：主机记录 `news`，类型 CNAME，记录值填 OSS 或 CDN 提供的**目标域名**（如 `xxx.oss-cn-hangzhou.aliyuncs.com` 或 CDN 分配的 CNAME），保存后等待生效。

完成后，国内用户访问 `https://news.wittywiz.cc` 将直接命中阿里云（及 CDN），不再依赖 GitHub，访问更稳定。部署更新时，只需重新上传 `web/` 下变更后的文件即可。
