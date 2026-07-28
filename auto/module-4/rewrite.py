import pandas as pd
import re

df = pd.read_csv('output/merged-reviews.csv')

def shorten_review(text):
    if pd.isna(text): return text
    text = str(text)
    
    # Remove verbose intro
    text = re.sub(r'^(We were looking for|I was searching for|I wanted something|We wanted something|I was hesitant to|I was nervous about|Ordering furniture online).*?[.!]\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(Every single guest|Everyone who visits|Every guest).*?[.!]\s+', 'A true show stopper! ', text, flags=re.IGNORECASE)
    
    # Cut excessive detail
    text = re.sub(r' sitting on our vintage area rug right by the fireplace', '', text)
    text = re.sub(r' It pairs beautifully with our.*?armchair\.', '', text)
    text = re.sub(r' holds our favorite novels and candle effortlessly\.', ' holds everything effortlessly.', text)
    
    # Standardize & shorten complaints/4-star reasons
    text = re.sub(r'(Taking 1 star off because|I gave 4 stars only because|I knocked off one star because|I took off one star just because)', '4 stars because', text, flags=re.IGNORECASE)
    text = re.sub(r'4 stars because.*?unpack safely\.', 'Heavy crate, needs two people to unpack.', text)
    text = re.sub(r'4 stars because.*?due to the weight\.', 'Needs two people to mount securely due to the weight.', text)
    text = re.sub(r'4 stars because.*?precise measuring\.', 'Takes some patience to align.', text)
    text = re.sub(r'4 stars because.*?carrier delays\.', 'Shipping took a few extra days.', text)
    text = re.sub(r'4 stars because.*?mount it safely\.', 'Heavy solid wood, definitely need two people to mount safely.', text)
    
    # Split sentences and keep the punchy ones
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if len(sentences) > 3:
        # Keep first two and last sentence, which usually contain the core review
        sentences = [sentences[0], sentences[1], sentences[-1]]
        
    return ' '.join(sentences)

def shorten_reply(text):
    if pd.isna(text): return text
    text = str(text)
    
    text = re.sub(r'^(Thank you for your review|Thank you for your feedback|Thank you for sharing your experience|Hi .*?, thank you).*?[.!]\s+', 'Thanks for your feedback! ', text, flags=re.IGNORECASE)
    text = re.sub(r'(We are so happy to hear|We are delighted that|We are thrilled that|We are so pleased to know).*?[.!]\s*', 'We are thrilled you love it! ', text, flags=re.IGNORECASE)
    text = re.sub(r'Because we craft our.*?heavy\.', 'Our solid wood pieces are heavy to ensure lifelong durability.', text, flags=re.IGNORECASE)
    text = re.sub(r'Since each piece is handcrafted.*?authentic character\.', 'Natural variations are part of its authentic charm.', text, flags=re.IGNORECASE)
    
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if len(sentences) > 2:
        return sentences[0] + ' ' + sentences[-1]
    return ' '.join(sentences)

df['body'] = df['body'].apply(shorten_review)
df['reply'] = df['reply'].apply(shorten_reply)

df.to_csv('output/merged-reviews.csv', index=False)
print("CSV rewritten successfully.")
