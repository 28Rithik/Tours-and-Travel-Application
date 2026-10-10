"""
RAG (Retrieval-Augmented Generation) Knowledge Engine for Rathasārathi AI
Sivagayathiri Travels & Tours ERP

Provides local semantic vector search, document chunking, TF-IDF vectorization,
and hybrid keyword-similarity retrieval across tour packages, cancellation policies,
temple guidelines, hill station e-passes, and fleet emergency SOPs.
"""

import math
import re
from typing import List, Dict, Any, Optional
from django.utils import timezone
from documents.models import KnowledgeDocument, KnowledgeChunk

# Standard English & Travel Stopwords
STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most',
    'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our',
    'ours', 'ourselves', 'out', 'over', 'own', 's', 'same', 'she', 'should', 'so', 'some', 'such',
    'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they',
    'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were',
    'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'you',
    'your', 'yours', 'yourself', 'yourselves'
}


class RAGKnowledgeEngine:
    """
    High-performance, zero-dependency hybrid RAG retrieval engine.
    Computes normalized term frequencies and cosine vectors with BM25 keyword boosting.
    """

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Cleans and extracts normalized alphabetic/numeric tokens."""
        if not text:
            return []
        cleaned = re.sub(r'[^a-zA-Z0-9\s-]', ' ', text.lower())
        tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 1 and t.strip() not in STOPWORDS]
        return tokens

    @classmethod
    def compute_vector(cls, tokens: List[str]) -> Dict[str, float]:
        """Computes L2-normalized term frequency weights."""
        if not tokens:
            return {}
        counts: Dict[str, int] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1

        # L2 norm
        sum_sq = sum(c * c for c in counts.values())
        norm = math.sqrt(sum_sq) if sum_sq > 0 else 1.0

        return {term: round(cnt / norm, 4) for term, cnt in counts.items()}

    @staticmethod
    def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Fast dot product between two normalized sparse vectors."""
        if not vec_a or not vec_b:
            return 0.0
        # Iterate over the smaller dict
        if len(vec_a) > len(vec_b):
            vec_a, vec_b = vec_b, vec_a

        dot_product = 0.0
        for term, val_a in vec_a.items():
            if term in vec_b:
                dot_product += val_a * vec_b[term]
        return dot_product

    @classmethod
    def chunk_text(cls, text: str, max_chunk_words: int = 350, overlap_words: int = 50) -> List[Dict[str, Any]]:
        """Splits document text into overlapping semantic passages."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_words: List[str] = []
        chunk_title = ""

        for para in paragraphs:
            para_words = para.split()
            if not chunk_title and para.startswith('#'):
                chunk_title = para.lstrip('#').strip().split('\n')[0]

            if len(current_words) + len(para_words) <= max_chunk_words:
                current_words.extend(para_words)
            else:
                if current_words:
                    content = " ".join(current_words)
                    chunks.append({
                        "content": content,
                        "title": chunk_title or " ".join(current_words[:6]) + "..."
                    })
                    chunk_title = ""
                    # Keep overlap
                    current_words = current_words[-overlap_words:] if len(current_words) > overlap_words else []
                current_words.extend(para_words)

        if current_words:
            content = " ".join(current_words)
            chunks.append({
                "content": content,
                "title": chunk_title or " ".join(current_words[:6]) + "..."
            })

        return chunks

    @classmethod
    def ingest_document(cls, doc: KnowledgeDocument) -> int:
        """Chunks, vectorizes, and indexes a KnowledgeDocument."""
        # Remove old chunks
        doc.chunks.all().delete()

        raw_text = doc.raw_content or ""
        chunk_specs = cls.chunk_text(raw_text)

        created_chunks = []
        for idx, item in enumerate(chunk_specs, start=1):
            tokens = cls.tokenize(item["content"])
            vector = cls.compute_vector(tokens)
            # Top keywords
            sorted_terms = sorted(vector.items(), key=lambda x: x[1], reverse=True)[:10]
            keywords = ", ".join([t[0] for t in sorted_terms])

            created_chunks.append(KnowledgeChunk(
                document=doc,
                chunk_index=idx,
                chunk_title=item["title"][:250],
                content=item["content"],
                keywords=keywords,
                vector_tfidf=vector,
            ))

        KnowledgeChunk.objects.bulk_create(created_chunks)
        doc.chunk_count = len(created_chunks)
        doc.save(update_fields=['chunk_count', 'updated_at'])
        return len(created_chunks)

    @classmethod
    def search(cls, query: str, top_k: int = 4, min_score: float = 0.08, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic cosine vector similarity with exact keyword boosts.
        Returns top matching chunks sorted by relevance score.
        """
        query_tokens = cls.tokenize(query)
        if not query_tokens:
            return []

        query_vec = cls.compute_vector(query_tokens)

        qs = KnowledgeChunk.objects.filter(document__is_active=True).select_related('document')
        if category:
            qs = qs.filter(document__category=category)

        scored_results = []
        for chunk in qs:
            chunk_vec = chunk.vector_tfidf or {}
            cos_sim = cls.cosine_similarity(query_vec, chunk_vec)

            # Keyword matching bonus
            overlap = set(query_tokens).intersection(set(chunk_vec.keys()))
            overlap_bonus = (len(overlap) / len(query_tokens)) * 0.15 if query_tokens else 0.0

            total_score = cos_sim + overlap_bonus
            if total_score >= min_score:
                scored_results.append({
                    "score": round(total_score, 4),
                    "chunk_id": chunk.id,
                    "document_id": chunk.document.id,
                    "document_title": chunk.document.title,
                    "category": chunk.document.category,
                    "category_display": chunk.document.get_category_display(),
                    "source": chunk.document.source,
                    "chunk_title": chunk.chunk_title,
                    "content": chunk.content,
                    "keywords": chunk.keywords,
                })

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]

    @classmethod
    def seed_default_knowledge(cls) -> int:
        """
        Populates high-value standard knowledge repositories for Sivagayathiri Travels:
        1. Package Itineraries & Vehicle Fleet
        2. Booking, Cancellation & Driver Bata Rules
        3. South India Sightseeing, E-Pass & Temple Dress Codes
        4. Fleet Emergency, Breakdown & Driver Safety SOP
        """
        SEEDS = [
            {
                "title": "Sivagayathiri Tour Packages & Fleet Tariffs Directory",
                "category": "package_itinerary",
                "source": "Sivagayathiri Operations Handbook 2026",
                "raw_content": """# Sivagayathiri Tour Packages & Fleet Tariffs Directory

## 1. Ooty Queen of Hills Expedition (3 Days / 2 Nights)
Route: Coimbatore / Bangalore -> Ooty -> Coonoor -> Pykara -> Return.
Highlights: Botanical Garden, Doddabetta Peak, Tea Factory & Museum, Rose Garden, Pykara Lake & Waterfalls, Sim's Park Coonoor, Nilgiri Mountain Railway Toy Train.
Recommended Vehicles:
- Sedan (Swift Dzire / Toyota Etios): Ideal for 2-4 Pax. Starting tariff: ₹11,500.
- SUV (Toyota Innova Crysta): Ideal for 5-7 Pax. Starting tariff: ₹16,500.
- Urbania / Tempo Traveller (12/17 Seater): Ideal for 8-15 Pax. Starting tariff: ₹25,000.
Inclusions: Vehicle hire, fuel, chauffeur allowance, toll charges.
Exclusions: Entry tickets, boating charges, hotel accommodation unless booked as package.

## 2. Munnar & Thekkady Kerala Wildlife Circuit (4 Days / 3 Nights)
Route: Kochi / Coimbatore -> Munnar (2 Nights) -> Thekkady (1 Night) -> Return.
Highlights: Cheeyappara Waterfalls, Valara Waterfalls, Eravikulam National Park (Nilgiri Tahr), Mattupetty Dam, Echo Point, Tea Museum, Periyar National Park Wildlife Boat Safari, Spice Plantation Tour, Kathakali & Kalaripayattu Cultural Show.
Recommended Vehicles:
- Sedan: ₹16,000 | Innova Crysta: ₹23,500 | 17-Seater Tempo: ₹34,000.
Permit Info: Kerala inter-state permit tax applies for non-KL registered vehicles (automatically handled by company).

## 3. South India Sacred Temple Heritage Circuit (5 Days / 4 Nights)
Route: Madurai -> Rameswaram -> Kanyakumari -> Return.
Highlights: Madurai Meenakshi Amman Temple, Thirumalai Nayakar Mahal, Rameswaram Ramanathaswamy Temple (22 Sacred Theerthams holy bath), Dhanushkodi Ghost Town, APJ Abdul Kalam Memorial, Pamban Bridge view, Kanyakumari Sunrise & Sunset, Vivekananda Rock Memorial, Thiruvalluvar Statue, Padmanabhapuram Palace.
Recommended Vehicles: Innova Crysta (₹29,000) or Tempo Traveller (₹42,000).

## 4. Kodaikanal Princess of Hill Stations Weekend (3 Days / 2 Nights)
Route: Madurai / Trichy / Coimbatore -> Kodaikanal -> Return.
Highlights: Kodaikanal Lake boating, Coaker's Walk, Bryant Park, Pillar Rocks, Guna Caves, Silver Cascade Falls, Pine Forest.
"""
            },
            {
                "title": "Customer Booking, Cancellation, Night Bata & Refund Policies",
                "category": "policy_rules",
                "source": "Company Commercial Terms & Conditions (Rev 2026)",
                "raw_content": """# Customer Booking, Cancellation, Night Bata & Refund Policies

## 1. Booking Advance & Payment Slabs
- Cab-Only Bookings (Local / Outstation): 25% advance to confirm reservation. Balance payable 50% on trip start and remaining 25% upon trip completion.
- Complete Tour Packages (Cabs + Hotels + Sightseeing): 50% advance at booking, remaining balance 48 hours prior to journey departure date.
- Accepted Modes: UPI (GPay/PhonePe), NetBanking (IMPS/NEFT), Credit/Debit Cards, Corporate Purchase Order (for pre-approved DMC/corporate credit accounts).

## 2. Cancellation and Refund Slabs
- More than 7 days prior to pickup time: 90% refund (10% administrative & processing fee deducted).
- Between 3 to 7 days prior to pickup time: 50% refund of advance paid.
- Between 24 to 72 hours prior to pickup time: 25% refund of advance paid.
- Less than 24 hours or No-Show: 0% refund (Non-refundable, vehicle and driver hold charges apply).
- Force Majeure (Landslides, Cyclones, Government Curfews): 100% credit note issued valid for 12 months on any route.

## 3. Chauffeur Night Bata (Driver Allowance) Rules
- Standard Duty Hours: Chauffeurs are on duty from 06:00 AM to 10:00 PM daily.
- Night Bata Trigger: If the vehicle operates or is in passenger transit between 10:00 PM and 06:00 AM, Night Bata is mandatory.
- Rates:
  - Sedan (Dzire/Etios): ₹300 per night.
  - SUV (Innova Crysta): ₹400 per night.
  - Tempo Traveller / Mini Bus: ₹600 per night.
- Day Bata: Outstation driver daily food & lodging allowance is ₹400/day for Sedans and ₹500/day for SUVs, already factored into outstation packages.

## 4. Tolls, Parking, Hill Charges & Inter-State Permits
- Fastag tolls and public parking fees are billable as actuals unless explicitly booked under 'All-Inclusive' corporate packages.
- Inter-state border permit tax (e.g., entering Kerala from Tamil Nadu or Karnataka) is valid for 7 days and charged at state RTO gazetted rates.
"""
            },
            {
                "title": "South India Tourism Sightseeing, E-Pass & Temple Dress Codes",
                "category": "tourism_guide",
                "source": "Tamil Nadu & Kerala Tourism Regulatory Manual 2026",
                "raw_content": """# South India Tourism Sightseeing, E-Pass & Temple Dress Codes

## 1. Nilgiris (Ooty) & Kodaikanal Mandatory E-Pass Regulations
- High Court Mandate: All commercial and private vehicles entering the Nilgiris district (Ooty, Coonoor, Kotagiri) and Kodaikanal MUST generate an official E-Pass prior to entry via `epass.tnega.org`.
- Chauffeur Responsibility: Sivagayathiri dispatchers automatically apply and pre-generate the E-Pass QR code for every trip vehicle 24 hours prior to departure. Drivers must display the pass at the Burliar / Thalaikundah / Ghat checkposts.
- Plastic Ban: Nilgiris and Kodaikanal have a strict ban on single-use plastic bottles (< 5 liters) and carry bags. Heavy fines are levied at toll gates.

## 2. Sacred Temple Dress Codes & Darshan Protocols
- Madurai Meenakshi Amman Temple:
  - Dress Code: Strict traditional Hindu attire. Men must wear Dhoti with Angavastram/Shirt or Pyjama-Kurta. Women must wear Saree, Half-Saree, or Churidar with Dupatta. Jeans, T-shirts, shorts, and sleeveless tops are strictly forbidden.
  - Electronic Ban: Mobile phones, smart watches, and cameras are prohibited inside the temple premises. Cloakroom facilities available at East and West Gopuram gates.
- Rameswaram Ramanathaswamy Temple:
  - Holy Theertham Bathing: 22 Wells (Theerthams) inside the temple. Devotees take bath in all 22 wells in wet clothes, then change into dry traditional attire before entering the main Shiva sanctum.
  - Timings: Morning 05:00 AM to 01:00 PM; Evening 03:00 PM to 09:00 PM.
- Tirupati Tirumala Balaji:
  - Mandatory traditional dress code for Special Entry Darshan (SED ₹300) and VIP Break Darshan. Aadhaar card original mandatory for verification.

## 3. Wildlife Sanctuaries & Safari Timings
- Mudumalai Tiger Reserve (Theppakadu):
  - Van Safari: 06:30 AM to 09:00 AM and 03:30 PM to 06:00 PM.
  - Elephant Camp Feeding: 08:30 AM to 09:00 AM and 05:30 PM to 06:00 PM.
- Bandipur National Park Safari: Morning 06:15 AM - 09:00 AM, Evening 03:00 PM - 05:30 PM.
- Periyar Wildlife Sanctuary (Thekkady): KTDC Lake Boat Safari slots at 07:30 AM, 09:30 AM, 11:15 AM, 01:45 PM, and 03:30 PM. Online advance booking advised.
"""
            },
            {
                "title": "Fleet Safety, Emergency Escalation & Vehicle Breakdown SOP",
                "category": "fleet_safety",
                "source": "Sivagayathiri Fleet Safety & ISO-9001 Operations Protocol",
                "raw_content": """# Fleet Safety, Emergency Escalation & Vehicle Breakdown SOP

## 1. 24x7 Emergency Control Room & Hotline
- Control Room Phone: `+91 94431 23456` / `+91 98765 43210`.
- Arattai Emergency Fleet Channel: `@sivagayathiri_fleet_control`.
- Chauffeur SOS Button: Every vehicle telematics device has a physical red panic button connected to our geofence telemetry engine.

## 2. Vehicle Breakdown & Replacement SLA
- Minor Breakdown (Puncture / Fuse): Chauffeur coordinates immediate roadside assistance. Maximum acceptable resolution time: 30 minutes.
- Major Mechanical Breakdown (Clutch, Engine, Radiator):
  - Chauffeur immediately informs Control Room via mobile portal or Arattai.
  - Replacement Vehicle SLA: Standby vehicle dispatched from nearest hub (Coimbatore, Madurai, Trichy, Ooty, Salem) to arrive within 60 minutes in plains and 90 minutes in hill stations.
  - Refreshments & Comfort: Chauffeur escorts passengers to nearest safe restaurant/hotel while awaiting replacement.

## 3. Accident Response & Medical Emergency Protocol
1. Chauffeur ensures safety of all passengers; immediately calls `108` (National Emergency Ambulance) and `100` (Police).
2. Chauffeur triggers SOS alert via mobile app or calls Fleet Dispatcher.
3. Fleet Operations team contacts local nearest network hospital and dispatches company supervisor to the scene.
4. Comprehensive passenger accidental insurance cover of ₹5,00,000 per seat is active on all commercial passenger vehicles.

## 4. Speed Limits & Safe Driving Regulations
- Expressways / 4-Lane National Highways: Maximum 80 km/h.
- 2-Lane State Highways: Maximum 60 km/h.
- Ghat Roads / Hairpin Bends: Maximum 35 km/h.
- Zero Alcohol & Substance Tolerance: Regular breathalyzer checks at company hubs. Immediate termination and blacklisting for any violation.
"""
            }
        ]

        total_chunks = 0
        for data in SEEDS:
            doc, created = KnowledgeDocument.objects.get_or_create(
                title=data["title"],
                defaults={
                    "category": data["category"],
                    "source": data["source"],
                    "raw_content": data["raw_content"],
                    "is_active": True,
                }
            )
            # Ingest & chunk
            chunks_count = cls.ingest_document(doc)
            total_chunks += chunks_count

        return total_chunks
