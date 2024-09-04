import PyPDF2

# Open the file in read-binary mode
file = open("paper.pdf", 'rb')
readPDF = PyPDF2.PdfReader(file)

# Iterate over the first two pages
for page_no in range(min(25, len(readPDF.pages))):
    page = readPDF.pages[page_no]
    text = page.extract_text()
    print(f"Content of page {page_no + 1}:\n{text}\n")
    
    # Extract URLs from Annotations
    if "/Annots" in page:
        annotations = page["/Annots"]
        for annot in annotations:
            annotation_object = annot.get_object()
            if "/A" in annotation_object:
                if "/URI" in annotation_object["/A"]:
                    print(f"URL found in annotations on page {page_no + 1}: {annotation_object['/A']['/URI']}")

# Close the file
file.close()
