# GroundNote Sunum Taslağı (Türkçe)

## Slayt 1 — Problem

- Öğrencilerin uzun ve özel ders belgelerinden hızlı yanıt alması gerekiyor.
- Bulut tabanlı yardımcılar belge ve soruları kullanıcının bilgisayarı dışına taşıyabilir.
- Amaç: sınırsız bir sohbet botu değil, kanıta dayalı yerel bir çalışma akışı.

## Slayt 2 — Proje Hedefi ve Kapsam

- Özel ve çevrimdışı-öncelikli RAG çalışma asistanı.
- PDF, DOCX, TXT ve Markdown desteği.
- Türkçe/İngilizce yanıtlar, kaynaklar ve yerel Bilgi Bankası.
- Birincil hedef Windows 11; portföy kalitesinde masaüstü uygulaması.

## Slayt 3 — Tek Şemada Yerel RAG

- Doğrula ve ayrıştır → parçala → göm → sakla.
- Soruyu göm → hibrit getir → sınırlı istem → yerel yanıt.
- Kaynak kimliklerini doğrula ve güvenilir meta veriyi göster.

## Slayt 4 — Uygulanan Mimari

- Streamlit arayüzü ve uygulama bağlamı.
- Python servis sınırları ve Foundry'den bağımsız sağlayıcı arayüzleri.
- SQLite meta veri/FTS5/float32 BLOB ve NumPy kosinüs benzerliği.
- Gömme ve sohbet için Microsoft Foundry Local.

## Slayt 5 — Güvenli Belge İşleme

- SHA-256 tekrar tespiti ve uygulama tarafından yönetilen kopyalar.
- Sayfa/bölüm bilgisini koruyan deterministik parçalama.
- PDF sayfa/metin sınırları ve DOCX ZIP/XML ön denetimi.
- Yalnızca bütünlük doğrulamasından sonra Ready durumu.

## Slayt 6 — Getirme ve Yanıt Üretimi

- Sözcüksel FTS5 ve anlamsal vektör sıralaması.
- Bölüm/başlık ve güçlü varlık kontrolleri yanlış dayanak riskini azaltır.
- Getirilen içerik talimat değil, güvenilmeyen kanıttır.
- Kanıt yetersizse kaynaksız ve açık ret yanıtı.

## Slayt 7 — Gizlilik ve Kaynak Güvenliği

- Bulut çıkarımı, telemetri, analitik ve kalıcı istem günlüğü yok.
- Belgeler, gömmeler, sorular, yanıtlar ve günlükler yerelde kalır.
- Tek GroundNote sohbet modeli; gömme/sohbet devri çakışmayı önler.
- Tek dosyalı eşzamanlı indeksleme; indeksleme sırasında sohbet kapalıdır.

## Slayt 8 — Test ve Performans

- Birim testleri sahte sağlayıcı kullanır; Foundry testleri açıkça ayrıdır.
- Lint, biçim, katı tip, regresyon, kapsam, UI, kurulum ve yayın testleri.
- CPU gömme ölçülen darboğazdır: 121 parçada 83,833 saniyenin 82,300 saniyesi.
- Ölçümler makineye ve iş yüküne özeldir; garanti değildir.

## Slayt 9 — Canlı Demo

- Kurgusal Lantern Lab el kitabını yükle.
- Yanıtlanabilir bir soru sor ve kaynakları göster.
- Desteklenmeyen uydu sorusunu sor ve kanıta dayalı reddi göster.
- Bilgi Bankası ve Yeni sohbet davranışını göster.

## Slayt 10 — Öğrenimler, Sınırlar ve Gelecek

- Basit sınırlar önizleme SDK'sı ve gizlilik değişikliklerini izole etti.
- Mevcut sınırlar: OCR, arka plan kuyruğu, kalıcı geçmiş ve yerel kurucu yok.
- Gelecek fikirleri: iptal, kalıcı indeksleme, OCR, hızlandırma, macOS ve imzalama.
- GroundNote 1.0.0 hedeflenen portföy kapsamını tamamlıyor.
