<div align="center">
  <h1>FAN-CE UI</h1>
  <p>FAN-CE 管理画面フロントエンド</p>
</div>

**日本語** | [English](./README.md) | [中文](./README.zh-CN.md)

## 紹介

FAN-CE UI は、FAN-CE の管理画面フロントエンドです。現在はバックエンド API と連携し、オミクスデータの管理、検索、表示を行う `apps/web-antd` を中心に開発しています。

> 現在の主要アプリ: `apps/web-antd`
>
> そのほかのアプリや共有パッケージは、テンプレートまたは共通基盤として保持されています。

## 主な特徴

- **最新技術スタック**：Vue 3やViteなどの最先端フロントエンド技術で開発
- **TypeScript**：アプリケーション規模のJavaScriptのための言語
- **モノレポ構成**：共有パッケージと複数アプリをまとめて管理
- **国際化**：多言語 UI に対応
- **権限管理**：動的メニューとルートベースのアクセス制御

## 開発

1. 依存関係をインストール

```bash
npm i -g corepack
pnpm install
```

2. 管理画面を開発モードで起動

```bash
pnpm dev:antd
```

3. 必要に応じてバックエンドも別途起動

```bash
cd ../../
scripts/dev/start-backend.sh
```

4. ビルド

```bash
pnpm build:antd
```

## ブラウザサポート

ローカル開発には `Chrome 80+` ブラウザを推奨します

モダンブラウザをサポートし、IEはサポートしません

| [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/edge/edge_48x48.png" alt="Edge" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Edge | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/firefox/firefox_48x48.png" alt="Firefox" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Firefox | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/chrome/chrome_48x48.png" alt="Chrome" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Chrome | [<img src="https://raw.githubusercontent.com/alrra/browser-logos/master/src/safari/safari_48x48.png" alt="Safari" width="24px" height="24px" />](http://godban.github.io/browsers-support-badges/)</br>Safari |
| :-: | :-: | :-: | :-: |
| 最新2バージョン | 最新2バージョン | 最新2バージョン | 最新2バージョン |

## ライセンス

[MIT](./LICENSE)
