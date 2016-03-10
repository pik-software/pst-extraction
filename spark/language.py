# Standard lib
import argparse
import json
import subprocess
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

# 3rd-party modules
from pyspark import SparkContext, SparkConf

SUPPORTED_LANGS = ['es','en']

def dump(x):
    return json.dumps(x)

def language(text):
    try:
        return detect(text)
    except LangDetectException:
        return 'en'

def translate(text, from_lang, to_lang='en'):
    return text

def translate_hack(text, from_lang, to_lang='en'):
    if not text.strip():
        return ""
    if not to_lang in SUPPORTED_LANGS:
        return text

    # TODO this is slow
    cmd = ['apertium' , from_lang+'-'+to_lang]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    out_text, err = p.communicate(text)

    return out_text if not out_text.startswith("Error: Mode") else text

def process_email(email):
    # default to en
    lang = 'en'

    if "body" in email:
        lang = language(email["body"])
        if not lang == 'en':
            translated = translate_hack(email["body"], lang, 'en')
            email["body_lang"]= lang
            email["body_translated"] = translated

    if "subject" in email:
        # TODO  -- fix this for now use body lang for subject because library seems to miscalculate it because of RE: FW: characters etc
        # lang = language(email["subject"])
        if not lang == 'en':
            translated = translate_hack(email["subject"], lang, 'en')
            email["subject_lang"] = lang
            email["subject_translated"] = translated

    for attachment in email["attachments"]:
        if "contents" in attachment:
            lang = language(attachment["contents"])
            if not lang == 'en':
                translated = translate_hack(attachment["contents"], lang, 'en')
                attachment["contents_lang"] = lang
                attachment["contents_translated"] = translated

    return email

def test():
    print process_email({'body':"hello world"})
    return

def process_patition(emails):
    for email in emails:
        yield process_email(email)

if __name__ == '__main__':
    desc='regexp extraction'
    parser = argparse.ArgumentParser(
        description=desc,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=desc)


    # TEST
    # test()
    # print "done"

    # SPARK

    parser.add_argument("input_content_path", help="input email or attachment content path")
    parser.add_argument("output_content_translated", help="output all text enriched with translation and language")
    args = parser.parse_args()

    conf = SparkConf().setAppName("Newman translate")
    sc = SparkContext(conf=conf)

    rdd_emails = sc.textFile(args.input_content_path).coalesce(50).map(lambda x: json.loads(x))
    rdd_emails.mapPartitions(lambda docs: process_patition(docs)).map(dump).saveAsTextFile(args.output_content_translated)