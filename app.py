# -- coding: utf-8 --
"""
app.py - SSDC 2025 E-Commerce Dashboard
With improved negative reviews analysis matching the top 5 lowest-rated categories
"""

import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Dashboard E-Commerce SSDC 2025",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Data Loading Function ---
@st.cache_data
def load_all_data():
    try:        
        # Memuat semua dataset
        data_files = {
            'customers': 'data/customers_dataset.csv',
            'geolocation': 'data/geolocation_dataset.csv',
            'order_items': 'data/order_items_dataset.csv',
            'order_payments': 'data/order_payments_dataset.csv',
            'order_reviews': 'data/order_reviews_dataset.csv',
            'orders': 'data/orders_dataset.csv',
            'product_translation': 'data/product_category_name_translation.csv',
            'products': 'data/products_dataset.csv',
            'sellers': 'data/sellers_dataset.csv',
            'closed_deals': 'data/closed_deals_dataset.csv',
            'marketing_leads': 'data/marketing_qualified_leads_dataset.csv'
        }

        loaded_data = {}
        for name, path in data_files.items():
            loaded_data[name] = pd.read_csv(path)

        # Merge datasets
        df_merged = loaded_data['orders'].copy()
        merge_steps = [
            (loaded_data['order_items'], 'order_id'),
            (loaded_data['products'], 'product_id'),
            (loaded_data['product_translation'], 'product_category_name'),
            (loaded_data['order_reviews'], 'order_id'),
            (loaded_data['customers'], 'customer_id'),
            (loaded_data['sellers'], 'seller_id'),
            (loaded_data['order_payments'], 'order_id')
        ]
        
        for df_to_merge, on_key in merge_steps:
            df_merged = pd.merge(df_merged, df_to_merge, on=on_key, how='left')
        
        df_merged = df_merged.drop_duplicates(subset=['order_id', 'order_item_id', 'review_id'])

        # Convert date columns
        date_cols = [
            'order_purchase_timestamp', 'order_approved_at',
            'order_delivered_carrier_date', 'order_delivered_customer_date',
            'order_estimated_delivery_date', 'shipping_limit_date',
            'review_creation_date', 'review_answer_timestamp'
        ]
        for col in date_cols:
            df_merged[col] = pd.to_datetime(df_merged[col], errors='coerce')

        # Feature engineering
        df_merged['delivery_duration_days'] = (df_merged['order_delivered_customer_date'] - df_merged['order_purchase_timestamp']).dt.days
        df_merged['delivery_performance_days'] = (df_merged['order_estimated_delivery_date'] - df_merged['order_delivered_customer_date']).dt.days

        return df_merged, loaded_data['geolocation']

    except FileNotFoundError as e:
        st.error(f"File tidak ditemukan: {e.filename}. Pastikan file CSV berada di dalam folder 'data/'.")
        return None, None
    except Exception as e:
        st.error(f"Terjadi error saat memuat atau memproses data: {str(e)}")
        return None, None

# --- 3. Load and Filter Data ---
df_main, df_geolocation = load_all_data()

if df_main is not None:
    st.sidebar.title("Kontrol Dasbor ⚙")
    st.sidebar.header("Filter Data")

    min_date = df_main['order_purchase_timestamp'].min().date()
    max_date = df_main['order_purchase_timestamp'].max().date()

    date_range = st.sidebar.date_input(
        "Rentang Tanggal Pembelian:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df_filtered = df_main[(df_main['order_purchase_timestamp'] >= start_date) & 
                             (df_main['order_purchase_timestamp'] <= end_date)].copy()
    else:
        df_filtered = df_main.copy()

    all_categories = sorted(df_filtered['product_category_name_english'].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Pilih Kategori Produk:", options=all_categories, default=all_categories
    )

    all_order_statuses = df_filtered['order_status'].dropna().unique().tolist()
    selected_order_statuses = st.sidebar.multiselect(
        "Pilih Status Pesanan:", options=all_order_statuses, default=['delivered']
    )
    
    df_filtered = df_filtered[
        df_filtered['product_category_name_english'].isin(selected_categories) &
        df_filtered['order_status'].isin(selected_order_statuses)
    ]

    # --- 4. Main Dashboard ---
    st.title("📊 E-Commerce Business Insight - SSDC 2025")
    st.write("Analisis untuk mendukung pengambilan keputusan strategis dalam meningkatkan pengalaman pembeli, kualitas produk, dan efisiensi logistik.")

    if df_filtered.empty:
        st.warning("Tidak ada data yang tersedia untuk filter yang dipilih. Silakan sesuaikan filter Anda di sidebar.")
    else:
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Penjualan", f"R$ {df_filtered['price'].sum():,.0f}")
        col2.metric("Jumlah Pesanan", f"{df_filtered['order_id'].nunique():,}")
        col3.metric("Rata-rata Skor Ulasan", f"{df_filtered['review_score'].mean():.2f} / 5")
        col4.metric("Rata-rata Waktu Pengiriman", f"{df_filtered['delivery_duration_days'].mean():.1f} Hari")
        st.markdown("---")

        # Main Tabs
        tab1, tab2, tab3 = st.tabs([
            "⭐ Kualitas & Performa Produk",
            "🚚 Logistik & Jangkauan Pasar",
            "🚀 Rekomendasi Strategis"
        ])

        # --- TAB 1: KUALITAS & PERFORMA PRODUK ---
        with tab1:
            st.subheader("Menganalisis Produk Mana yang Berhasil dan Mana yang Perlu Perbaikan")
            
            analysis_choice = st.selectbox(
                "Pilih Jenis Analisis Produk:",
                ("Performa Penjualan Produk", "Analisis Ulasan Pelanggan")
            )

            if analysis_choice == "Performa Penjualan Produk":
                st.markdown("##### Top 10 Kategori Produk Berdasarkan Total Penjualan")
                top_categories = df_filtered.groupby('product_category_name_english')['price'].sum().nlargest(10).reset_index()
                fig = px.bar(top_categories, x='price', y='product_category_name_english',
                           labels={'price': 'Total Penjualan (R$)', 'product_category_name_english': 'Kategori Produk'},
                           orientation='h', color='price', color_continuous_scale=px.colors.sequential.Viridis)
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("""
                *Insight:*
                - Kategori tertentu mendominasi penjualan.
                - Deskripsi yang lebih panjang berpotensi menaikkan kepuasan.

                *Rekomendasi:*
                - Fokus promosi pada kategori top.
                - Perbaiki deskripsi dan foto produk.
                - Kurasi ulang kategori berat ekstrem.
                """)

            elif analysis_choice == "Analisis Ulasan Pelanggan":
                st.markdown("##### Distribusi Skor Ulasan Produk")
                st.write("Mayoritas pelanggan memberikan ulasan positif (skor 4 dan 5), namun ulasan negatif (skor 1 dan 2) perlu menjadi perhatian khusus.")
                review_score_counts = df_filtered['review_score'].value_counts().sort_index().reset_index()
                review_score_counts.columns = ['review_score', 'count']
                fig_review = px.bar(review_score_counts, x='review_score', y='count',
                                     labels={'review_score': 'Skor Ulasan', 'count': 'Jumlah Ulasan'},
                                     color='review_score', color_continuous_scale=px.colors.sequential.Plasma, text='count')
                fig_review.update_layout(title="Distribusi Skor Ulasan (1=Buruk, 5=Sangat Baik)")
                st.plotly_chart(fig_review, use_container_width=True)

                st.markdown("##### Kategori Produk dengan Rata-rata Skor Ulasan Terendah (Top 5)")
                avg_reviews = df_filtered.groupby('product_category_name_english')['review_score'].mean().nsmallest(5).reset_index()
                fig_low = px.bar(avg_reviews, x='product_category_name_english', y='review_score',
                               labels={'product_category_name_english': 'Kategori Produk', 
                                      'review_score': 'Rata-rata Skor Ulasan'},
                               color='review_score', color_continuous_scale=px.colors.sequential.Reds)
                st.plotly_chart(fig_low, use_container_width=True)

                # Improved Negative Reviews Analysis
                st.markdown("### Analisis Ulasan Negatif untuk Kategori dengan Skor Terendah")
                
                for idx, row in avg_reviews.iterrows():
                    category = row['product_category_name_english']
                    avg_score = row['review_score']
                    
                    st.markdown(f"#### Kategori: {category} (Rata-rata: {avg_score:.2f}/5)")
                    
                    # Get negative reviews for this category
                    neg_reviews = df_filtered[
                        (df_filtered['product_category_name_english'] == category) & 
                        (df_filtered['review_score'].isin([1, 2]))
                    ]
                    
                    if not neg_reviews.empty:
                        # Calculate stats
                        total = len(df_filtered[df_filtered['product_category_name_english'] == category])
                        neg_count = len(neg_reviews)
                        neg_percent = (neg_count / total) * 100
                        
                        st.markdown(f"""
                        - **Total Ulasan:** {total}
                        - **Ulasan Negatif (1-2 bintang):** {neg_count} ({neg_percent:.1f}%)
                        """)
                        
                        # Show sample reviews
                        samples = neg_reviews[['review_score', 'review_comment_message']].dropna().sample(min(3, len(neg_reviews)))
                        if not samples.empty:
                            st.markdown("**Contoh Ulasan Negatif:**")
                            for _, review in samples.iterrows():
                                st.markdown(f"""
                                - **{review['review_score']}/5:** {review['review_comment_message']}
                                """)
                        else:
                            st.info("Tidak ada ulasan teks untuk kategori ini")
                    else:
                        st.info("Tidak ditemukan ulasan negatif (skor 1-2) untuk kategori ini")
                    
                    st.markdown("---")

        # --- TAB 2: LOGISTIK & JANGKAUAN PASAR ---
        with tab2:
            st.subheader("Mengevaluasi Efisiensi Pengiriman dan Persebaran Pelanggan")

            analysis_choice_logistics = st.selectbox(
                "Pilih Jenis Analisis Logistik:",
                ("Analisis Kinerja Pengiriman", "Distribusi Geografis Pelanggan")
            )

            if analysis_choice_logistics == "Analisis Kinerja Pengiriman":
                st.markdown("##### Distribusi Durasi Pengiriman Aktual (Hari)")
                st.write("Memahami berapa lama waktu yang dibutuhkan dari pesanan dibuat hingga sampai ke tangan pelanggan.")
                fig_delivery_dist = px.histogram(df_filtered.dropna(subset=['delivery_duration_days']), x='delivery_duration_days',
                                                 nbins=50, labels={'delivery_duration_days': 'Durasi Pengiriman (Hari)'})
                fig_delivery_dist.update_layout(title="Distribusi Durasi Pengiriman (dari Beli hingga Tiba)")
                st.plotly_chart(fig_delivery_dist, use_container_width=True)

                st.markdown("##### Performa Pengiriman Terhadap Estimasi (Hari)")
                st.info("Nilai positif berarti pengiriman lebih cepat dari estimasi. Nilai negatif berarti lebih lambat (terlambat).")
                fig_delivery_perf = px.histogram(df_filtered.dropna(subset=['delivery_performance_days']), x='delivery_performance_days',
                                                 nbins=50, labels={'delivery_performance_days': 'Selisih Hari (Estimasi - Aktual)'})
                fig_delivery_perf.update_layout(title="Histogram Performa Pengiriman Terhadap Estimasi")
                st.plotly_chart(fig_delivery_perf, use_container_width=True)
            
            elif analysis_choice_logistics == "Distribusi Geografis Pelanggan":
                st.markdown("##### Peta Persebaran Pelanggan")
                st.write("Visualisasi lokasi pelanggan untuk mengidentifikasi pasar utama dan potensi area ekspansi.")
                geo_group = df_geolocation.groupby('geolocation_zip_code_prefix').agg(
                    lat=('geolocation_lat', 'mean'),
                    lon=('geolocation_lng', 'mean')
                ).reset_index()

                cust_geo = pd.merge(df_filtered[['customer_id', 'customer_zip_code_prefix', 'customer_city', 'customer_state']].drop_duplicates(), 
                                    geo_group, 
                                    left_on='customer_zip_code_prefix', 
                                    right_on='geolocation_zip_code_prefix', 
                                    how='left').dropna(subset=['lat', 'lon'])
                
                fig_map = px.scatter_mapbox(
                    cust_geo.sample(n=min(5000, len(cust_geo))),
                    lat="lat", lon="lon",
                    hover_name="customer_city", hover_data={"customer_state": True},
                    color_discrete_sequence=["#1a237e"], zoom=3, height=500
                )
                fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig_map, use_container_width=True)

                st.markdown("##### Distribusi Pelanggan Berdasarkan Provinsi")
                
                state_map = {
                    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 'CE': 'Ceará', 
                    'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso',
                    'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná',
                    'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
                    'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo',
                    'SE': 'Sergipe', 'TO': 'Tocantins'
                }
                
                customer_state_dist = df_filtered['customer_state'].value_counts().nlargest(10).reset_index()
                customer_state_dist.columns = ['state_abbr', 'count']
                customer_state_dist['state_full_name'] = customer_state_dist['state_abbr'].map(state_map)
                
                fig_state = px.bar(customer_state_dist, x='count', y='state_full_name',
                                   labels={'count': 'Jumlah Pelanggan', 'state_full_name': 'Provinsi'},
                                   orientation='h', color='count', color_continuous_scale=px.colors.sequential.Plasma, text='count')
                fig_state.update_layout(yaxis={'categoryorder':'total ascending'}, title="Top 10 Provinsi dengan Pelanggan Terbanyak")
                st.plotly_chart(fig_state, use_container_width=True)
                st.markdown("""
                Insight:
                - Sebaran pelanggan terkonsentrasi di wilayah perkotaan besar.
                - Wilayah tertentu menunjukkan potensi pertumbuhan.

                Rekomendasi:
                - Target promosi wilayah padat.
                - Eksplorasi wilayah dengan penetrasi rendah.
                """)

        # --- TAB 3: REKOMENDASI STRATEGIS ---
        with tab3:
            st.header("🚀 Rekomendasi Strategis untuk Peningkatan Perusahaan")

            st.warning("""
            ASPEK PRIORITAS: PENINGKATAN KUALITAS PRODUK & PENGALAMAN PELANGGAN
            
            Berdasarkan analisis, kami merekomendasikan untuk memprioritaskan peningkatan kualitas produk, terutama pada kategori yang secara konsisten menerima skor ulasan rendah.
            """)

            st.subheader("Alasan Prioritas:")
            st.markdown("""
            * Dampak Langsung pada Kepuasan: Data pada tab "Kualitas & Performa Produk" menunjukkan korelasi kuat antara kategori produk tertentu dengan ulasan negatif. Ini adalah sumber utama ketidakpuasan.
            * Potensi Kehilangan Penjualan: Ulasan buruk adalah penghalang terbesar bagi calon pelanggan baru. Memperbaikinya akan secara langsung meningkatkan konversi.
            * Efisiensi Biaya: Produk berkualitas rendah meningkatkan biaya operasional melalui proses pengembalian, penggantian, dan layanan pelanggan yang intensif.
            """)

            st.subheader("Langkah-langkah yang Dapat Diambil:")
            st.markdown("""
            1.  Evaluasi Penjual (Seller) pada Kategori Bermasalah: Identifikasi penjual yang produknya sering mendapat ulasan buruk di kategori-kategori terendah. Berikan pelatihan atau peringatan untuk meningkatkan standar kualitas.
            2.  Perbaikan Deskripsi & Foto Produk: Analisis ulasan negatif untuk memahami apakah ada ketidaksesuaian antara ekspektasi (dari deskripsi/foto) dan produk asli. Pastikan informasi yang diberikan akurat.
            3.  Fokus pada Kategori Unggulan: Alokasikan lebih banyak sumber daya pemasaran dan promosi untuk kategori produk terlaris dengan ulasan bagus untuk memaksimalkan citra merek yang positif dan mendorong penjualan lebih lanjut.
            4.  Optimalkan Logistik di Pasar Utama: Gunakan data dari tab "Logistik & Jangkauan Pasar" untuk memprioritaskan perbaikan logistik di provinsi dengan pelanggan terbanyak (seperti São Paulo, Rio de Janeiro, Minas Gerais) untuk memastikan pengalaman pengiriman terbaik bagi basis pelanggan terbesar Anda.
            """)
            
            st.success("Dengan fokus pada kualitas produk dan didukung oleh perbaikan logistik yang ditargetkan, perusahaan dapat meningkatkan loyalitas pelanggan, reputasi merek, dan pada akhirnya, pertumbuhan penjualan yang berkelanjutan.")

# Pesan jika data gagal dimuat di awal
else:
    st.title("📊 E-Commerce Business Insight - SSDC 2025")
    st.error("Gagal memuat data. Mohon periksa kembali file CSV Anda dan pastikan berada di dalam folder 'data/'.")
