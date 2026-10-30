import AppKit
import Foundation

guard CommandLine.arguments.count == 2 else {
    fputs("Usage: swift fiesta-card.swift OUTPUT.png\n", stderr); exit(2)
}
let w = 720, h = 1280
guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0), let ctx = NSGraphicsContext(bitmapImageRep: bitmap) else { exit(1) }
NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = ctx
let navy = NSColor(calibratedRed: 0.12, green: 0.10, blue: 0.30, alpha: 1)
let pink = NSColor(calibratedRed: 0.94, green: 0.24, blue: 0.51, alpha: 1)
let cyan = NSColor(calibratedRed: 0.33, green: 0.91, blue: 0.84, alpha: 1)
let yellow = NSColor(calibratedRed: 1.00, green: 0.84, blue: 0.36, alpha: 1)
navy.setFill(); NSRect(x: 0, y: 0, width: w, height: h).fill()
pink.setFill()
for y in stride(from: 110, through: 190, by: 20) {
    NSBezierPath(roundedRect: NSRect(x: 80, y: y, width: 560, height: 5), xRadius: 2, yRadius: 2).fill()
}
cyan.setStroke()
for x in [150.0, 410.0] {
    let box = NSBezierPath(roundedRect: NSRect(x: x, y: 720, width: 160, height: 120), xRadius: 20, yRadius: 20)
    box.lineWidth = 7; box.stroke()
    let tail = NSBezierPath(); tail.lineWidth = 7
    tail.move(to: NSPoint(x: x + 45, y: 720)); tail.line(to: NSPoint(x: x + 25, y: 690)); tail.line(to: NSPoint(x: x + 90, y: 720)); tail.stroke()
}
let link = NSBezierPath(); link.lineWidth = 7; link.move(to: NSPoint(x: 310, y: 780)); link.line(to: NSPoint(x: 410, y: 780)); link.stroke()
let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .center
let font = NSFont(name: "HelveticaNeue-Bold", size: 50) ?? NSFont.boldSystemFont(ofSize: 50)
let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: yellow, .paragraphStyle: paragraph]
("Escuchar. Aclarar.\nInterpretar." as NSString).draw(in: NSRect(x: 55, y: 440, width: 610, height: 155), withAttributes: attrs)
let small: [NSAttributedString.Key: Any] = [.font: NSFont.boldSystemFont(ofSize: 26), .foregroundColor: cyan, .paragraphStyle: paragraph, .kern: 3]
("CADA DOS DÍAS" as NSString).draw(in: NSRect(x: 80, y: 275, width: 560, height: 45), withAttributes: small)
NSGraphicsContext.restoreGraphicsState()
guard let data = bitmap.representation(using: .png, properties: [:]) else { exit(1) }
try data.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
