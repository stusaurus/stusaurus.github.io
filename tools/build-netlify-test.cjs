'use strict';
const fs = require('node:fs');
const path = require('node:path');

const deploymentURL = process.env.URL || process.env.DEPLOY_PRIME_URL;
if (!deploymentURL) {
  throw new Error('Netlify must supply URL or DEPLOY_PRIME_URL; cannot build a sitemap for an unknown host.');
}
const siteOrigin = new URL(deploymentURL).origin;
if (!siteOrigin.startsWith('https://') || siteOrigin.includes('github.io')) {
  throw new Error('Expected an independent HTTPS Netlify origin.');
}
const output = path.join(process.cwd(), '.netlify-gsc-site');
fs.mkdirSync(output, { recursive: true });
const write = (name, content) => fs.writeFileSync(path.join(output, name), content, { encoding: 'utf8' });
const escaped = siteOrigin.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

write('index.html', [
  '<!doctype html>',
  '<html lang="ja"><head>',
  '<meta charset="utf-8">',
  '<meta name="viewport" content="width=device-width,initial-scale=1">',
  '<title>Search Console Sitemap Diagnostic</title>',
  '<meta name="description" content="別ホストでのサイトマップ取得検証用の公開ページです。">',
  '<link rel="canonical" href="' + siteOrigin + '/">',
  '</head><body><main>',
  '<h1>Sitemap Fetch Diagnostic</h1>',
  '<p>This unique page is hosted on Netlify to diagnose Search Console sitemap fetching.</p>',
  '</main></body></html>'
].join('\n') + '\n');
write('robots.txt', 'User-agent: *\nAllow: /\nSitemap: ' + siteOrigin + '/sitemap.xml\n');
write('sitemap.xml', [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  '  <url><loc>' + escaped + '/</loc></url>',
  '</urlset>'
].join('\n') + '\n');
write('sitemap.txt', siteOrigin + '/\n');
write('googlef35e71acece62b67.html', 'google-site-verification: googlef35e71acece62b67.html\n');

const text = fs.readFileSync(path.join(output, 'sitemap.xml'), 'utf8');
if (!text.includes('<loc>' + escaped + '/</loc>')) {
  throw new Error('Sitemap generation assertion failed');
}
console.log('Netlify control site prepared:', siteOrigin, 'files:', fs.readdirSync(output).sort().join(', '));
