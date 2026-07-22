"""
Content Generator Module
========================
Generates scripts, titles, and descriptions for YouTube Shorts videos.
Supports both template-based (FREE) and AI-based generation.
"""
import random
import json
from typing import Dict, Optional
from config.settings import Config, NICHES
from loguru import logger


# ============================================================
# CONTENT LIBRARY - Huge collection of pre-written content
# ============================================================

MOTIVATIONAL_CONTENT = [
    {
        'topic': 'Kekuatan Konsistensi',
        'fact': 'Orang sukses bukan yang paling berbakat, tapi yang paling konsisten',
        'motivation': 'Setiap langkah kecil yang kamu ambil hari ini membentuk masa depanmu',
        'closing': 'kesuksesan adalah hasil dari kebiasaan baik yang dilakukan berulang-ulang'
    },
    {
        'topic': 'Mindset Pemenang',
        'fact': 'Thomas Edison gagal 10.000 kali sebelum berhasil menciptakan lampu',
        'motivation': 'kegagalan bukan akhir, tapi pelajaran yang membawamu lebih dekat ke tujuan',
        'closing': 'setiap kegagalan adalah satu langkah lebih dekat menuju kesuksesan'
    },
    {
        'topic': 'Mulai dari Sekarang',
        'fact': 'Waktu terbaik untuk memulai adalah 10 tahun yang lalu. Waktu terbaik kedua adalah sekarang',
        'motivation': 'jangan tunggu kondisi sempurna karena itu tidak akan pernah datang',
        'closing': 'yang membedakan pemimpi dan pejuang adalah tindakan nyata'
    },
    {
        'topic': 'Investasi pada Diri Sendiri',
        'fact': 'Warren Buffett mengatakan investasi terbaik adalah investasi pada diri sendiri',
        'motivation': 'ilmu dan skill yang kamu punya tidak bisa dicuri siapapun',
        'closing': 'luangkan minimal 1 jam setiap hari untuk belajar hal baru'
    },
    {
        'topic': 'Berani Keluar Zona Nyaman',
        'fact': 'Pertumbuhan terbesar terjadi di luar zona nyaman kita',
        'motivation': 'rasa takut adalah tanda bahwa kamu sedang bertumbuh',
        'closing': 'satu-satunya cara untuk berkembang adalah berani mencoba hal baru'
    },
    {
        'topic': 'Fokus pada Proses',
        'fact': 'Orang Jepang punya filosofi Kaizen: perbaikan kecil setiap hari menghasilkan perubahan besar',
        'motivation': 'jangan obsesi dengan hasil, nikmati setiap prosesnya',
        'closing': 'perbaikan 1% setiap hari berarti 37 kali lebih baik dalam setahun'
    },
    {
        'topic': 'Kekuatan Pikiran Positif',
        'fact': 'Penelitian menunjukkan pikiran positif meningkatkan produktivitas hingga 31%',
        'motivation': 'pikiran adalah magnet, apa yang kamu pikirkan akan kamu tarik',
        'closing': 'mulai harimu dengan gratitude dan lihat bagaimana hidupmu berubah'
    },
    {
        'topic': 'Disiplin adalah Kebebasan',
        'fact': 'Jocko Willink, mantan Navy SEAL, mengatakan disiplin sama dengan kebebasan',
        'motivation': 'disiplin memberimu kebebasan untuk mencapai apapun yang kamu mau',
        'closing': 'bangun pagi, olahraga, belajar. Tiga kebiasaan yang mengubah hidup'
    },
    {
        'topic': 'Kekuatan Bertahan',
        'fact': 'Bambu China tidak terlihat tumbuh selama 5 tahun pertama karena menguatkan akarnya di bawah tanah',
        'motivation': 'kadang perjuanganmu tidak terlihat hasilnya, tapi percayalah prosesnya bekerja',
        'closing': 'pada tahun ke-6, bambu itu tumbuh 24 meter dalam 6 minggu. Sabarmu akan berbuah'
    },
    {
        'topic': 'Kebiasaan Kecil Berdampak Besar',
        'fact': 'James Clear dalam Atomic Habits mengatakan kebiasaan kecil menghasilkan perubahan luar biasa',
        'motivation': 'kamu tidak perlu perubahan drastis, cukup 2 menit setiap hari untuk memulai',
        'closing': 'mulai kecil, tetap konsisten, dan saksikan transformasimu'
    },
]

FACTS_CONTENT = [
    {
        'topic': 'Otak Manusia',
        'fact_1': 'Otak manusia menghasilkan listrik yang cukup untuk menyalakan lampu LED',
        'fact_2': 'otak kita memproses 70.000 pikiran setiap hari',
        'fact_3': 'otak tidak bisa merasakan sakit karena tidak memiliki reseptor rasa sakit'
    },
    {
        'topic': 'Luar Angkasa',
        'fact_1': 'Satu hari di Venus lebih lama dari satu tahun di Venus',
        'fact_2': 'di luar angkasa, astronot bisa tumbuh hingga 5 cm lebih tinggi',
        'fact_3': 'ada planet yang seluruhnya terbuat dari berlian bernama 55 Cancri e'
    },
    {
        'topic': 'Tubuh Manusia',
        'fact_1': 'DNA dalam satu sel manusia jika direntangkan panjangnya 2 meter',
        'fact_2': 'tubuh manusia menghasilkan sel darah merah baru setiap 4 bulan',
        'fact_3': 'hidung manusia bisa mendeteksi lebih dari 1 triliun bau berbeda'
    },
    {
        'topic': 'Lautan',
        'fact_1': 'Lebih dari 80% lautan belum pernah dieksplorasi manusia',
        'fact_2': 'di dasar laut ada air terjun terbalik yang lebih besar dari Niagara',
        'fact_3': 'tekanan di titik terdalam Mariana Trench sama dengan 50 jumbo jet di atas tubuhmu'
    },
    {
        'topic': 'Teknologi',
        'fact_1': 'Smartphone kamu lebih bertenaga dari semua komputer NASA saat misi Apollo 11',
        'fact_2': 'internet memakai energi lebih banyak dari seluruh penerbangan di dunia',
        'fact_3': 'lebih banyak orang di dunia punya ponsel daripada sikat gigi'
    },
    {
        'topic': 'Hewan',
        'fact_1': 'Gurita punya 3 jantung dan darahnya berwarna biru',
        'fact_2': 'lumba-lumba tidur dengan satu mata terbuka karena setengah otaknya tetap terjaga',
        'fact_3': 'lebah madu bisa mengenali wajah manusia'
    },
    {
        'topic': 'Sejarah',
        'fact_1': 'Kleopatra hidup lebih dekat ke era pembuatan iPhone daripada pembangunan Piramida',
        'fact_2': 'Oxford University lebih tua dari peradaban Aztec',
        'fact_3': 'Nintendo didirikan tahun 1889, jauh sebelum era video game'
    },
    {
        'topic': 'Psikologi',
        'fact_1': 'Otak kita tidak bisa membedakan antara pengalaman nyata dan imajinasi yang vivid',
        'fact_2': 'mendengarkan musik memicu pelepasan dopamin sama seperti makan cokelat',
        'fact_3': 'kita cenderung lebih kreatif saat mengantuk karena otak kurang bisa memfilter ide'
    },
]

TECH_CONTENT = [
    {
        'topic': 'Keyboard Shortcut Tersembunyi',
        'intro': 'Ada shortcut keyboard yang 90% orang tidak tahu',
        'steps': 'tekan Windows + V untuk clipboard history, atau Ctrl + Shift + T untuk buka tab yang tertutup',
        'benefit': 'kamu bisa hemat waktu hingga 30 menit setiap hari'
    },
    {
        'topic': 'Keamanan Password',
        'intro': 'Password 8 karakter bisa dibobol dalam 5 menit',
        'steps': 'gunakan minimal 12 karakter dengan kombinasi huruf, angka, dan simbol. Lebih baik lagi gunakan passphrase',
        'benefit': 'akunmu akan 100 kali lebih aman dari serangan brute force'
    },
    {
        'topic': 'Dark Mode',
        'intro': 'Dark mode bukan cuma soal estetika',
        'steps': 'pada layar OLED, dark mode bisa hemat baterai hingga 40%. Aktifkan di Settings > Display',
        'benefit': 'mata kamu lebih nyaman dan baterai lebih awet, terutama di malam hari'
    },
    {
        'topic': 'WiFi Lemot',
        'intro': 'WiFi lemot bisa diperbaiki tanpa upgrade paket',
        'steps': 'pindahkan router ke tempat tinggi di tengah rumah, jauhkan dari microwave dan cermin, dan ganti channel WiFi',
        'benefit': 'speed internet bisa meningkat 2 hingga 3 kali lipat tanpa biaya tambahan'
    },
    {
        'topic': 'AI Gratis untuk Produktivitas',
        'intro': 'Ada banyak tools AI gratis yang bisa meningkatkan produktivitasmu',
        'steps': 'gunakan ChatGPT untuk brainstorming, Canva AI untuk desain, dan Remove.bg untuk edit foto',
        'benefit': 'pekerjaanmu bisa selesai 5 kali lebih cepat dengan bantuan AI'
    },
]

HEALTH_CONTENT = [
    {
        'topic': 'Tidur Berkualitas',
        'tip': 'Kualitas tidur lebih penting dari kuantitas',
        'research': 'tidur dalam ruangan gelap meningkatkan produksi melatonin hingga 58%',
        'action': 'matikan semua layar 1 jam sebelum tidur dan pastikan kamar gelap total'
    },
    {
        'topic': 'Minum Air Putih',
        'tip': 'Dehidrasi ringan bisa menurunkan fungsi otak hingga 25%',
        'research': 'minum air putih 30 menit sebelum makan membantu menurunkan berat badan',
        'action': 'siapkan botol air 2 liter dan habiskan sebelum malam'
    },
    {
        'topic': 'Olahraga 7 Menit',
        'tip': 'Kamu tidak butuh gym mahal untuk sehat',
        'research': 'latihan interval 7 menit sama efektifnya dengan 30 menit jogging',
        'action': 'lakukan 7 menit high intensity workout setiap pagi sebelum mandi'
    },
    {
        'topic': 'Postur Tubuh',
        'tip': 'Duduk terlalu lama lebih berbahaya dari merokok menurut beberapa penelitian',
        'research': 'berdiri dan bergerak setiap 30 menit mengurangi risiko penyakit jantung hingga 33%',
        'action': 'pasang timer setiap 30 menit untuk stretching minimal 2 menit'
    },
]

FINANCE_CONTENT = [
    {
        'topic': 'Aturan 50/30/20',
        'tip': 'Atur keuanganmu dengan rumus 50/30/20. 50% untuk kebutuhan, 30% untuk keinginan, 20% untuk tabungan',
        'insight': 'kebanyakan orang menghabiskan lebih dari 70% pendapatan untuk keinginan, bukan kebutuhan',
        'action': 'catat semua pengeluaranmu selama 1 minggu dan kategorikan'
    },
    {
        'topic': 'Compound Interest',
        'tip': 'Einstein menyebut compound interest sebagai keajaiban dunia ke-8',
        'insight': 'investasi 1 juta per bulan dengan return 10% per tahun menjadi 2 miliar dalam 30 tahun',
        'action': 'sisihkan minimal 20% penghasilan untuk investasi, mulai dari sekarang'
    },
    {
        'topic': 'Dana Darurat',
        'tip': 'Siapkan dana darurat 6 hingga 12 bulan pengeluaran sebelum berinvestasi',
        'insight': 'tanpa dana darurat, kamu akan terpaksa menjual investasi saat harga turun',
        'action': 'buka rekening terpisah khusus dana darurat dan auto-debit setiap gajian'
    },
    {
        'topic': 'Passive Income',
        'tip': 'Orang kaya rata-rata punya 7 sumber pendapatan',
        'insight': 'mengandalkan satu sumber income sama seperti berdiri di satu kaki',
        'action': 'pilih satu skill yang bisa menghasilkan passive income dan kembangkan selama 6 bulan'
    },
]

NATURE_CONTENT = [
    {
        'topic': 'Hutan Hujan',
        'intro': 'Hutan hujan Amazon menghasilkan 20% oksigen dunia',
        'fact': 'di dalamnya terdapat lebih dari 40.000 spesies tanaman dan 1.300 spesies burung yang belum semuanya teridentifikasi',
    },
    {
        'topic': 'Gunung Berapi',
        'intro': 'Indonesia memiliki 127 gunung berapi aktif, terbanyak di dunia',
        'fact': 'letusan Krakatau tahun 1883 terdengar hingga 4.800 km jauhnya, setara dari Jakarta ke Australia',
    },
    {
        'topic': 'Aurora Borealis',
        'intro': 'Aurora terjadi ketika partikel matahari bertabrakan dengan atmosfer bumi',
        'fact': 'fenomena ini juga terjadi di planet lain seperti Jupiter dan Saturnus dengan warna yang berbeda',
    },
]

PSYCHOLOGY_CONTENT = [
    {
        'topic': 'Efek Dunning-Kruger',
        'intro': 'Orang yang tahu sedikit sering merasa paling pintar, sementara ahli justru meragukan dirinya',
        'fact': 'ini disebut efek Dunning-Kruger. Solusinya adalah terus belajar dan tetap rendah hati',
    },
    {
        'topic': 'Paradox of Choice',
        'intro': 'Terlalu banyak pilihan justru membuat kita tidak bahagia',
        'fact': 'penelitian menunjukkan orang yang diberi 6 pilihan lebih puas daripada yang diberi 24 pilihan. Batasi opsimu untuk hidup lebih tenang',
    },
    {
        'topic': 'Habit Loop',
        'intro': 'Setiap kebiasaan terdiri dari 3 komponen: cue, routine, dan reward',
        'fact': 'untuk mengubah kebiasaan buruk, jangan hilangkan rutinitasnya tapi ganti dengan yang lebih baik sambil mempertahankan cue dan reward yang sama',
    },
]

# Master content map
CONTENT_LIBRARY = {
    'motivational': MOTIVATIONAL_CONTENT,
    'facts': FACTS_CONTENT,
    'tech': TECH_CONTENT,
    'health': HEALTH_CONTENT,
    'finance': FINANCE_CONTENT,
    'nature': NATURE_CONTENT,
    'psychology': PSYCHOLOGY_CONTENT,
}


def generate_script(niche: str = 'motivational', topic: str = '', language: str = 'id') -> Dict:
    """
    Generate a complete script for YouTube Shorts.
    
    Uses template-based generation (FREE) or OpenAI if configured.
    
    Args:
        niche: Content niche/category
        topic: Optional specific topic
        language: Language code (id/en)
    
    Returns:
        Dict with title, script, hashtags, and search_keywords
    """
    # Try AI generation if OpenAI key is available
    if Config.OPENAI_API_KEY:
        try:
            return _generate_with_ai(niche, topic, language)
        except Exception as e:
            logger.warning(f"AI generation failed, falling back to templates: {e}")
    
    # Template-based generation (FREE)
    return _generate_from_templates(niche, topic, language)


def _generate_from_templates(niche: str, topic: str, language: str) -> Dict:
    """Generate content using pre-built templates and content library."""
    
    niche_data = NICHES.get(niche, NICHES['motivational'])
    content_list = CONTENT_LIBRARY.get(niche, MOTIVATIONAL_CONTENT)
    
    # Select random content
    content = random.choice(content_list)
    
    # Build script based on niche
    if niche == 'motivational':
        title = f"💪 {content['topic']} - Motivasi Hari Ini"
        script = (
            f"Tahukah kamu? {content['fact']}. "
            f"Ingat, {content['motivation']}. "
            f"Jangan pernah menyerah, karena {content['closing']}. "
            f"Follow untuk motivasi setiap hari!"
        )
    elif niche == 'facts':
        title = f"🤯 Fakta Mengejutkan: {content['topic']}"
        script = (
            f"Fakta mengejutkan tentang {content['topic']}! "
            f"{content['fact_1']}. "
            f"Tidak hanya itu, {content['fact_2']}. "
            f"Yang lebih menarik lagi, {content['fact_3']}. "
            f"Follow untuk fakta menarik lainnya!"
        )
    elif niche == 'tech':
        title = f"💻 Tips Tech: {content['topic']}"
        script = (
            f"Tips teknologi hari ini tentang {content['topic']}! "
            f"{content['intro']}. "
            f"Caranya mudah, {content['steps']}. "
            f"Dengan tips ini, {content['benefit']}. "
            f"Save video ini dan share ke temanmu!"
        )
    elif niche == 'health':
        title = f"🏃 Tips Sehat: {content['topic']}"
        script = (
            f"Mau hidup lebih sehat? Simak tips tentang {content['topic']}! "
            f"{content['tip']}. "
            f"Menurut penelitian, {content['research']}. "
            f"Mulai dari sekarang, {content['action']}. "
            f"Like dan follow untuk tips kesehatan lainnya!"
        )
    elif niche == 'finance':
        title = f"💰 Tips Keuangan: {content['topic']}"
        script = (
            f"Tips keuangan yang wajib kamu tahu tentang {content['topic']}! "
            f"{content['tip']}. "
            f"Banyak orang tidak sadar bahwa {content['insight']}. "
            f"Mulai {content['action']} dari sekarang. "
            f"Follow untuk tips keuangan setiap hari!"
        )
    elif niche == 'nature':
        title = f"🌍 Keajaiban Alam: {content['topic']}"
        script = (
            f"Alam selalu memukau kita! Mari bahas tentang {content['topic']}. "
            f"{content['intro']}. "
            f"Fakta menariknya, {content['fact']}. "
            f"Sungguh menakjubkan! Follow untuk konten alam lainnya!"
        )
    elif niche == 'psychology':
        title = f"🧠 Psikologi: {content['topic']}"
        script = (
            f"Fakta psikologi yang perlu kamu tahu tentang {content['topic']}! "
            f"{content['intro']}. "
            f"Yang menarik, {content['fact']}. "
            f"Share ke teman yang perlu tahu ini!"
        )
    else:
        # Default/generic
        title = f"📌 {content.get('topic', 'Tips Hari Ini')}"
        script = f"Konten menarik hari ini! {json.dumps(content, ensure_ascii=False)}"
    
    # Generate search keywords for stock media
    search_keywords = _get_search_keywords(niche, content.get('topic', ''))
    
    return {
        'title': title,
        'script': script,
        'hashtags': niche_data['hashtags'],
        'search_keywords': search_keywords,
        'niche': niche,
        'topic': content.get('topic', '')
    }


def _generate_with_ai(niche: str, topic: str, language: str) -> Dict:
    """Generate content using OpenAI API (optional, paid)."""
    import openai
    
    client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    niche_data = NICHES.get(niche, NICHES['motivational'])
    
    lang_instruction = "in Indonesian (Bahasa Indonesia)" if language == 'id' else "in English"
    topic_instruction = f" about '{topic}'" if topic else ""
    
    prompt = f"""Create a YouTube Shorts script {lang_instruction} for the niche: {niche_data['name']}{topic_instruction}.

Requirements:
- Duration: 30-50 seconds when spoken
- Hook in first 3 seconds
- Engaging and informative
- End with a call-to-action (follow/like/share)
- Natural speaking tone

Return ONLY a JSON object with:
- "title": catchy title with emoji (max 100 chars)
- "script": the full narration script
- "search_keywords": 3-5 English keywords for finding stock footage
"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a viral YouTube Shorts content creator. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.8
    )
    
    result = json.loads(response.choices[0].message.content)
    
    return {
        'title': result.get('title', 'Video Shorts'),
        'script': result.get('script', ''),
        'hashtags': niche_data['hashtags'],
        'search_keywords': result.get('search_keywords', ''),
        'niche': niche,
        'topic': topic
    }


def _get_search_keywords(niche: str, topic: str) -> str:
    """Generate search keywords for finding stock media."""
    keyword_map = {
        'motivational': ['success', 'motivation', 'sunrise', 'achievement', 'running', 'mountain top'],
        'facts': ['science', 'space', 'technology', 'nature', 'documentary', 'discovery'],
        'tech': ['computer', 'smartphone', 'coding', 'technology', 'digital', 'innovation'],
        'health': ['fitness', 'healthy food', 'exercise', 'yoga', 'running', 'meditation'],
        'finance': ['money', 'business', 'stock market', 'office', 'success', 'growth'],
        'nature': ['nature', 'ocean', 'mountain', 'forest', 'wildlife', 'landscape'],
        'psychology': ['brain', 'thinking', 'mind', 'books', 'learning', 'meditation'],
        'history': ['ancient', 'monument', 'history', 'architecture', 'civilization'],
    }
    
    keywords = keyword_map.get(niche, ['nature', 'beautiful', 'cinematic'])
    
    # Add topic-related keywords
    if topic:
        keywords.insert(0, topic.lower())
    
    return ', '.join(random.sample(keywords, min(4, len(keywords))))


def generate_description(title: str, script: str, hashtags: list, niche: str) -> str:
    """Generate a YouTube-optimized description."""
    niche_data = NICHES.get(niche, NICHES['motivational'])
    
    description = f"""{title}

{script[:150]}...

📌 Jangan lupa LIKE, COMMENT, dan SUBSCRIBE untuk konten menarik lainnya!

{' '.join(hashtags)}
#shorts #viral #fyp

---
Video ini dibuat dengan AI automation.
"""
    return description.strip()


def get_random_content(niche: str) -> Dict:
    """Get random content data for a niche (used by scheduler)."""
    content_list = CONTENT_LIBRARY.get(niche, MOTIVATIONAL_CONTENT)
    return random.choice(content_list)
