const fs = require('fs');
const path = require('path');

function cleanXML(inputFile, outputFile) {
    // Read the input file
    const content = fs.readFileSync(inputFile, 'utf-8');

    // Extract all items using regex
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    const wordRegex = /<word>([\s\S]*?)<\/word>/;
    const transRegex = /<trans><!\[CDATA\[([\s\S]*?)\]\]><\/trans>/;
    const tagsRegex = /<tags>([\s\S]*?)<\/tags>/;

    const items = [];
    let match;

    while ((match = itemRegex.exec(content)) !== null) {
        const itemContent = match[1];

        const wordMatch = itemContent.match(wordRegex);
        const transMatch = itemContent.match(transRegex);
        const tagsMatch = itemContent.match(tagsRegex);

        if (wordMatch && transMatch) {
            const word = wordMatch[1].trim();
            const trans = transMatch[1].trim();
            const tags = tagsMatch ? tagsMatch[1].trim() : '';

            items.push({ word, trans, tags });
        }
    }

    // Build the cleaned XML
    const outputLines = ['<wordbook>'];

    items.forEach(item => {
        outputLines.push('<item>');
        outputLines.push(`  <word>${item.word}</word>`);
        outputLines.push(`  <trans><![CDATA[${item.trans}]]></trans>`);
        if (item.tags) {
            outputLines.push(`  <tags>${item.tags}</tags>`);
        }
        outputLines.push('</item>');
    });

    outputLines.push('</wordbook>');

    // Write to output file
    fs.writeFileSync(outputFile, outputLines.join('\n'), 'utf-8');

    console.log(`Cleaned XML saved to: ${outputFile}`);
    console.log(`Total items processed: ${items.length}`);
}

// Main execution
const inputFile = path.join(__dirname, '文化.xml');
const outputFile = path.join(__dirname, '文化_cleaned.xml');

cleanXML(inputFile, outputFile);
