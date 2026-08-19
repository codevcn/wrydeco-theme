import sys
with open('templates/blogs.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add button next to searchSubmitBtn
btn_html = """                <button type="button" id="searchSubmitBtn" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
                    Tìm kiếm
                </button>
                <button type="button" id="toggleFilterBtn" class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors" title="Bộ lọc nâng cao">
                    <iconify-icon icon="mdi:filter-variant" class="text-lg"></iconify-icon>
                </button>"""

text = text.replace("""                <button type="button" id="searchSubmitBtn" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
                    Tìm kiếm
                </button>""", btn_html)

# Add advanced filters block
filters_html = """        </div>

        <!-- Advanced Filters Section -->
        <div id="advancedFilters" class="hidden mb-4 p-4 bg-white rounded-lg border border-gray-200 shadow-sm transition-all">
            <h3 class="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                <iconify-icon icon="mdi:filter-outline"></iconify-icon> Bộ lọc nâng cao
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                    <label class="block text-xs font-medium text-gray-700 mb-1">Loại thời gian</label>
                    <select id="filterDateType" class="w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm py-2 px-3 border">
                        <option value="created_at">Ngày tạo (Created At)</option>
                        <option value="updated_at">Ngày cập nhật (Updated At)</option>
                        <option value="published_at">Ngày xuất bản (Published At)</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-700 mb-1">Từ ngày & giờ</label>
                    <input type="datetime-local" id="filterDateFrom" class="w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm py-2 px-3 border">
                </div>
                <div>
                    <label class="block text-xs font-medium text-gray-700 mb-1">Đến ngày & giờ</label>
                    <input type="datetime-local" id="filterDateTo" class="w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm py-2 px-3 border">
                </div>
            </div>
            <div class="mt-4 flex justify-end">
                <button type="button" id="clearFilterBtn" class="mr-2 inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-gray-700 hover:bg-gray-100 transition-colors">Xóa bộ lọc</button>
                <button type="button" id="applyFilterBtn" class="inline-flex items-center px-3 py-1.5 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 transition-colors">Áp dụng lọc</button>
            </div>
        </div>

        <div class="mb-4 flex items-center justify-end text-sm text-gray-600 bg-gray-50 px-4 py-3 rounded-lg border border-gray-200">"""

text = text.replace("""        </div>

        <div class="mb-4 flex items-center justify-end text-sm text-gray-600 bg-gray-50 px-4 py-3 rounded-lg border border-gray-200">""", filters_html)

# Update Javascript
js_patch = """        document.getElementById('searchSubmitBtn').addEventListener('click', function() {
            loadData();
        });
        
        document.getElementById('toggleFilterBtn').addEventListener('click', function() {
            const filterDiv = document.getElementById('advancedFilters');
            if (filterDiv.classList.contains('hidden')) {
                filterDiv.classList.remove('hidden');
                this.classList.add('bg-indigo-50', 'border-indigo-300', 'text-indigo-700');
            } else {
                filterDiv.classList.add('hidden');
                this.classList.remove('bg-indigo-50', 'border-indigo-300', 'text-indigo-700');
            }
        });

        document.getElementById('applyFilterBtn').addEventListener('click', function() {
            loadData();
        });

        document.getElementById('clearFilterBtn').addEventListener('click', function() {
            document.getElementById('filterDateFrom').value = '';
            document.getElementById('filterDateTo').value = '';
            loadData();
        });

        document.getElementById('searchInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                loadData();
            }
        });"""

text = text.replace("""        document.getElementById('searchSubmitBtn').addEventListener('click', function() {
            loadData();
        });

        document.getElementById('searchInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                loadData();
            }
        });""", js_patch)

# Update loadData to append filter params
load_data_patch = """            const dateType = document.getElementById('filterDateType').value;
            const dateFrom = document.getElementById('filterDateFrom').value;
            const dateTo = document.getElementById('filterDateTo').value;

            let url = `/blogs?sort=${sortVal}&search=${encodeURIComponent(searchInput)}`;
            if (dateFrom) url += `&date_type=${dateType}&date_from=${dateFrom}`;
            if (dateTo) url += `&date_to=${dateTo}`;
            
            if (direction === 'next' && currentCursors.end) {"""

text = text.replace("""            let url = `/blogs?sort=${sortVal}&search=${encodeURIComponent(searchInput)}`;
            if (direction === 'next' && currentCursors.end) {""", load_data_patch)

with open('templates/blogs.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patched blogs.html")
