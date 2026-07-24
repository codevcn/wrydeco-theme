import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Insert Column Toggle Area
col_toggle_html = '''        <!-- Column Toggle Area -->
        <div class="mb-6 bg-white p-4 rounded-xl shadow-[0_2px_10px_-4px_rgba(0,0,0,0.1)] border border-gray-100">
            <div class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <svg class="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"></path></svg>
                Hiển thị cột
            </div>
            <div class="flex flex-wrap gap-4" id="column-toggles">
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="1" checked><span class="ml-2 text-sm text-gray-700">STT</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="2" checked><span class="ml-2 text-sm text-gray-700">ID</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="3" checked><span class="ml-2 text-sm text-gray-700">Hình ảnh</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="4" checked><span class="ml-2 text-sm text-gray-700">Sản phẩm</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="5" checked><span class="ml-2 text-sm text-gray-700">Product Type</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="6" checked><span class="ml-2 text-sm text-gray-700">Giá</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="7" checked><span class="ml-2 text-sm text-gray-700">Tùy chọn</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="8" checked><span class="ml-2 text-sm text-gray-700">Collections</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="9" checked><span class="ml-2 text-sm text-gray-700">Media</span></label>
                <label class="inline-flex items-center cursor-pointer"><input type="checkbox" class="col-toggle form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" data-col="10" checked><span class="ml-2 text-sm text-gray-700">Ngày tạo</span></label>
            </div>
        </div>
'''
html = html.replace('            </form>\n        </div>\n', '            </form>\n        </div>\n' + col_toggle_html)

# 2. Add header "Ngày tạo"
html = html.replace(
    '<th scope="col" class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Media</th>\n                        </tr>',
    '<th scope="col" class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Media</th>\n                            <th scope="col" class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Ngày tạo</th>\n                        </tr>'
)

# 3. Add column "Ngày tạo"
html = html.replace(
    '                                </div>\n                            </td>\n                        </tr>',
    '                                </div>\n                            </td>\n                            <td class="px-6 py-5 text-sm whitespace-nowrap text-gray-500 font-medium">{{ product.createdAt }}</td>\n                        </tr>'
)

# 4. Add JS
js_logic = '''
        // Logic for column toggle
        const colToggles = document.querySelectorAll('.col-toggle');
        
        function applyColumnVisibility(colIndex, isVisible) {
            const styleId = 'toggle-col-' + colIndex;
            let styleEl = document.getElementById(styleId);
            
            if (!isVisible) {
                if (!styleEl) {
                    styleEl = document.createElement('style');
                    styleEl.id = styleId;
                    styleEl.innerHTML = `table th:nth-child(${colIndex}), table td:nth-child(${colIndex}) { display: none !important; }`;
                    document.head.appendChild(styleEl);
                }
            } else {
                if (styleEl) styleEl.remove();
            }
        }

        function loadColumnPrefs() {
            const prefs = JSON.parse(localStorage.getItem('colPrefs')) || {};
            colToggles.forEach(toggle => {
                const colIndex = toggle.getAttribute('data-col');
                if (prefs[colIndex] !== undefined) {
                    toggle.checked = prefs[colIndex];
                }
                applyColumnVisibility(colIndex, toggle.checked);
            });
        }

        function saveColumnPrefs() {
            const prefs = {};
            colToggles.forEach(toggle => {
                prefs[toggle.getAttribute('data-col')] = toggle.checked;
            });
            localStorage.setItem('colPrefs', JSON.stringify(prefs));
        }

        colToggles.forEach(toggle => {
            toggle.addEventListener('change', function() {
                applyColumnVisibility(this.getAttribute('data-col'), this.checked);
                saveColumnPrefs();
            });
        });

        loadColumnPrefs();
'''
html = html.replace(
    '        // Đóng lightbox khi nhấn phím Esc',
    js_logic + '\n        // Đóng lightbox khi nhấn phím Esc'
)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Updated index.html")
