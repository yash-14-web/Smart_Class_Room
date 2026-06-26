import os
import pypdf
from django.conf import settings
from materials.models import Material

# In-memory cache for parsed materials: material_id -> {'mtime': float, 'chunks': list}
PARSED_MATERIALS_CACHE = {}

def extract_text_from_material(material):
    """
    Parses a PDF or code/text material and returns its full text contents.
    Utilizes caching to avoid re-parsing on every query.
    """
    material_id = material.id
    file_path = material.file.path
    
    # Check if file exists
    if not os.path.exists(file_path):
        return ""
        
    mtime = os.path.getmtime(file_path)
    
    # Check cache
    if material_id in PARSED_MATERIALS_CACHE:
        cached = PARSED_MATERIALS_CACHE[material_id]
        if cached['mtime'] == mtime:
            return cached['text']
            
    # Extract text based on file type
    text = ""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        try:
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            text = "\n".join(pages_text)
        except Exception as e:
            text = f"[Error reading PDF: {str(e)}]"
    else:
        # Check if text-based code or notes file
        text_extensions = {'.py', '.txt', '.js', '.java', '.cpp', '.c', '.html', '.css', '.json', '.md', '.sql'}
        if ext in text_extensions:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except Exception as e:
                text = f"[Error reading text file: {str(e)}]"
                
    # Cache the result
    PARSED_MATERIALS_CACHE[material_id] = {
        'mtime': mtime,
        'text': text
    }
    
    return text

def chunk_text(text, chunk_size=800, overlap=150):
    """Splits text into chunks of roughly chunk_size characters with overlap."""
    if not text:
        return []
        
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
        
    return chunks

def score_chunk(query, chunk):
    """
    Computes a simple term-matching score between the query and the chunk.
    Excludes common stopwords to prevent bias.
    """
    stopwords = {'what', 'is', 'how', 'to', 'the', 'a', 'an', 'and', 'or', 'in', 'on', 'for', 'of', 'with', 'about', 'by'}
    query_words = [w.strip('?.!,"\'').lower() for w in query.split() if w.strip('?.!,"\'').lower() not in stopwords]
    
    if not query_words:
        return 0
        
    chunk_lower = chunk.lower()
    score = 0
    for word in query_words:
        if len(word) > 1:
            # Add points for every occurrence of a query word in the chunk
            score += chunk_lower.count(word)
            
    return score

def get_course_context(course, query):
    """
    Searches all uploaded materials for the course, chunks the text,
    and returns the top 3 most relevant chunks based on the query.
    """
    materials = Material.objects.filter(course=course)
    all_chunks = []
    
    for material in materials:
        text = extract_text_from_material(material)
        if text:
            chunks = chunk_text(text)
            for chunk in chunks:
                all_chunks.append({
                    'chunk': chunk,
                    'title': material.title,
                    'filename': material.filename()
                })
                
    if not all_chunks:
        return ""
        
    # Score chunks
    scored_chunks = []
    for entry in all_chunks:
        score = score_chunk(query, entry['chunk'])
        if score > 0:
            scored_chunks.append((score, entry))
            
    # Sort chunks by score descending
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Retrieve top 3 chunks
    top_entries = [entry for _, entry in scored_chunks[:3]]
    
    # If no matching chunks found, fallback to top 2 general chunks of the syllabus/notes
    if not top_entries:
        top_entries = all_chunks[:2]
        
    # Combine chunks into context string
    context_parts = []
    for entry in top_entries:
        context_parts.append(
            f"--- From Material: {entry['title']} ({entry['filename']}) ---\n"
            f"{entry['chunk'].strip()}"
        )
        
    return "\n\n".join(context_parts)
