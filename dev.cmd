@echo off
call "%~dp0scripts\lead-capture-test\init-test-src.cmd"
echo "Starting Shopify Theme Development Server..."
shopify theme dev --store wrydeco.myshopify.com --store-password 123456 --host 127.0.0.1