/**
 * face.js — Rostro paramétrico con perfiles anatómicos reales
 * 
 * Construye la cabeza usando secciones transversales (slices) en Y:
 * 15 slices desde mentón hasta frente, cada uno con forma ovalada
 * que se deforma según la anatomía: mandíbula, pómulos, ojos, etc.
 */

const HoudiniFace = {
    head: null,
    wireframe: null,
    material: null,
    wireframeMaterial: null,

    // ─── 15 slices de la cabeza (de abajo arriba) ───
    // Cada slice: { y, rx, rz, offsetX, offsetZ }
    // y = altura normalizada (0=mentón, 1=frente)
    // rx = radio horizontal (ancho)
    // rz = radio frontal (profundidad)
    // offsetX = desplazamiento lateral (0 = centrado)
    // offsetZ = desplazamiento frontal (- = más atrás)
    headSlices: [
        // Mentón (0.00) — punta redondeada
        { y: 0.00, rx: 0.10, rz: 0.08, ofX: 0, ofZ: 0.10 },
        // Mandíbula baja (0.08)
        { y: 0.08, rx: 0.22, rz: 0.14, ofX: 0, ofZ: 0.08 },
        // Mandíbula media (0.15)
        { y: 0.15, rx: 0.32, rz: 0.18, ofX: 0, ofZ: 0.05 },
        // Mandíbula alta / boca (0.22)
        { y: 0.22, rx: 0.38, rz: 0.20, ofX: 0, ofZ: 0.02 },
        // Boca (0.28)
        { y: 0.28, rx: 0.40, rz: 0.21, ofX: 0, ofZ: 0.00 },
        // Pómulos (0.35) — el punto más ancho
        { y: 0.35, rx: 0.42, rz: 0.22, ofX: 0, ofZ: 0.00 },
        // Pómulos altos (0.42)
        { y: 0.42, rx: 0.41, rz: 0.21, ofX: 0, ofZ: -0.02 },
        // Ojos (0.50) — se estrecha un poco
        { y: 0.50, rx: 0.38, rz: 0.20, ofX: 0, ofZ: -0.04 },
        // Ceja / frente baja (0.58)
        { y: 0.58, rx: 0.36, rz: 0.19, ofX: 0, ofZ: -0.05 },
        // Frente media (0.66)
        { y: 0.66, rx: 0.34, rz: 0.18, ofX: 0, ofZ: -0.04 },
        // Frente alta (0.75)
        { y: 0.75, rx: 0.32, rz: 0.17, ofX: 0, ofZ: -0.03 },
        // Frente superior (0.83)
        { y: 0.83, rx: 0.28, rz: 0.15, ofX: 0, ofZ: -0.02 },
        // Coronilla baja (0.90)
        { y: 0.90, rx: 0.22, rz: 0.12, ofX: 0, ofZ: 0.00 },
        // Coronilla (0.96)
        { y: 0.96, rx: 0.14, rz: 0.08, ofX: 0, ofZ: 0.02 },
        // Top (1.00)
        { y: 1.00, rx: 0.06, rz: 0.04, ofX: 0, ofZ: 0.04 },
    ],

    // ─── Deformaciones locales para rasgos faciales ───
    // Se aplican como offsets a los vértices de cada slice
    
    createGeometry() {
        const SEGMENTS_X = 48;  // puntos alrededor de cada slice
        const slices = this.headSlices;
        const numSlices = slices.length;
        
        const positions = [];
        const uvs = [];
        const normals = [];
        const indices = [];
        const edgeData = [];

        // Generar vértices por slice
        for (let s = 0; s < numSlices; s++) {
            const sl = slices[s];
            
            // Escala de tamaño general
            const scale = 0.55;
            const baseRx = sl.rx * scale;
            const baseRz = sl.rz * scale;
            
            for (let i = 0; i < SEGMENTS_X; i++) {
                const theta = (i / SEGMENTS_X) * Math.PI * 2;
                const cosT = Math.cos(theta);
                const sinT = Math.sin(theta);
                
                // Posición base — elipse
                let x = baseRx * Math.sin(theta);  // sin para que 0 sea adelante
                let z = baseRz * cosT;
                let y = sl.y * 1.2 - 0.1;  // escalamos altura y centramos
                
                // ─── DEFORMACIONES ANATÓMICAS ───
                
                // 1. NARIZ (entre theta ~ -0.5 a 0.5 en la parte frontal)
                // La nariz sobresale en el frente entre slices de boca a ojos
                const isFront = (cosT > 0.7);
                const noseHeight = this._gauss(sl.y, 0.30, 0.08);  // centrado en y=0.30
                if (isFront && noseHeight > 0.01) {
                    const noseZ = noseHeight * 0.12 * (cosT - 0.7) / 0.3;
                    const noseFalloff = (cosT - 0.7) / 0.3;
                    z += noseZ * Math.max(0, noseFalloff);
                    // Punta de la nariz se eleva un poco
                    if (cosT > 0.95) y += noseHeight * 0.02;
                }
                
                // 2. CEJAS (protuberancia supraorbitaria)
                const isBrow = (cosT > 0.3 && cosT < 0.9) && 
                               (sl.y > 0.50 && sl.y < 0.62);
                if (isBrow) {
                    const browZ = this._gauss(sl.y, 0.56, 0.04) * 0.04;
                    z += browZ * (1 - Math.abs(cosT - 0.6) / 0.3);
                }
                
                // 3. PÓMULOS (ensanchamiento lateral)
                const isCheekSide = (Math.abs(sinT) > 0.6 && cosT > 0);
                if (isCheekSide && sl.y > 0.25 && sl.y < 0.48) {
                    const cheekW = this._gauss(sl.y, 0.37, 0.06) * 0.05;
                    x += cheekW * Math.sign(sinT);
                }
                
                // 4. MANDÍBULA (estrechamiento en la quijada)
                const isJaw = (cosT > 0.2 && sl.y > 0.05 && sl.y < 0.20);
                if (isJaw) {
                    const jawNarrow = this._gauss(sl.y, 0.12, 0.05) * 0.04;
                    x *= (1 - jawNarrow);
                }
                
                // 5. HUNDIMIENTO DE OJOS (ligero retroceso)
                const isEyeArea = (cosT > 0.3 && cosT < 0.8) && 
                                  (sl.y > 0.44 && sl.y < 0.56);
                if (isEyeArea) {
                    const eyeDepth = this._gauss(sl.y, 0.50, 0.04) * 0.03;
                    z -= eyeDepth * (1 - Math.abs(cosT - 0.55) / 0.25);
                }
                
                // 6. BOCA (hendidura horizontal)
                const isMouth = (cosT > 0.7) && (sl.y > 0.22 && sl.y < 0.32);
                if (isMouth) {
                    const mouthZ = this._gauss(sl.y, 0.27, 0.03) * 0.025;
                    z += mouthZ * (cosT - 0.7) / 0.3;
                }
                
                // 7. SIENES (retroceso lateral en la zona temporal)
                const isTemple = (Math.abs(sinT) > 0.5) && (sl.y > 0.55 && sl.y < 0.70);
                if (isTemple) {
                    const templeNarrow = this._gauss(sl.y, 0.62, 0.06) * 0.04;
                    x *= (1 - templeNarrow);
                }
                
                positions.push(x, y, z);
                uvs.push(i / SEGMENTS_X, sl.y);
                
                // Normal aproximada hacia afuera
                const nx = Math.sin(theta) * 0.8;
                const nz = Math.cos(theta) * 0.6;
                const len = Math.sqrt(nx * nx + nz * nz + 0.2 * 0.2);
                normals.push(nx / len, 0.2 / len, nz / len);
                
                // Edge data — más brillo en bordes para efecto holográfico
                const edgeVal = Math.abs(cosT) * 0.7 + 0.3;
                edgeData.push(edgeVal);
            }
        }

        // Generar índices (triángulos entre slices)
        for (let s = 0; s < numSlices - 1; s++) {
            for (let i = 0; i < SEGMENTS_X; i++) {
                const a = s * SEGMENTS_X + i;
                const b = s * SEGMENTS_X + (i + 1) % SEGMENTS_X;
                const c = (s + 1) * SEGMENTS_X + i;
                const d = (s + 1) * SEGMENTS_X + (i + 1) % SEGMENTS_X;
                indices.push(a, b, c);
                indices.push(b, d, c);
            }
        }

        // Crear geometría
        const geom = new THREE.BufferGeometry();
        geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
        geom.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
        geom.setAttribute('aEdge', new THREE.Float32BufferAttribute(edgeData, 1));
        geom.setIndex(indices);
        geom.computeVertexNormals();

        return geom;
    },

    // Helper: campana de Gauss
    _gauss(x, center, width) {
        const d = (x - center) / width;
        return Math.exp(-d * d * 2);
    },

    create(scene) {
        const geometry = this.createGeometry();

        // ─── Shader del holograma ───
        this.material = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uColor: { value: new THREE.Color(0x00d4ff) },
                uGlowColor: { value: new THREE.Color(0x66eeff) },
            },
            vertexShader: `
                attribute float aEdge;
                varying float vEdge;
                varying vec2 vUv;
                varying vec3 vNormal;
                uniform float uTime;
                
                void main() {
                    vEdge = aEdge;
                    vUv = uv;
                    vNormal = normalize(normalMatrix * normal);
                    
                    // Leve respiración
                    vec3 pos = position;
                    float breath = sin(uTime * 1.5) * 0.003;
                    pos.y += breath;
                    
                    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
            fragmentShader: `
                varying float vEdge;
                varying vec2 vUv;
                varying vec3 vNormal;
                uniform vec3 uColor;
                uniform vec3 uGlowColor;
                uniform float uTime;
                
                void main() {
                    // Color base holográfico
                    vec3 color = uColor * (0.5 + 0.5 * vEdge);
                    
                    // Brillo rim (luz de borde)
                    float rim = 1.0 - abs(vNormal.z);
                    rim = pow(rim, 2.0) * 0.8;
                    color += uGlowColor * rim;
                    
                    // Líneas de scan horizontal
                    float scanLine = sin(vUv.y * 200.0 + uTime * 2.0) * 0.15 + 0.85;
                    color *= scanLine;
                    
                    // Líneas de scan vertical (más sutiles)
                    float scanV = sin(vUv.x * 80.0 - uTime * 1.5) * 0.05 + 0.95;
                    color *= scanV;
                    
                    // Bordes más brillantes
                    color += uGlowColor * vEdge * 0.2;
                    
                    // Transparencia
                    float alpha = 0.45 + 0.3 * vEdge;
                    alpha -= 0.1 * (1.0 - abs(vNormal.z));
                    
                    // Pulsación suave
                    float pulse = sin(uTime * 0.8) * 0.05 + 0.95;
                    color *= pulse;
                    
                    gl_FragColor = vec4(color, alpha);
                }
            `,
            transparent: true,
            side: THREE.DoubleSide,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
        });

        this.head = new THREE.Mesh(geometry, this.material);

        // ─── Wireframe ───
        const wireGeom = new THREE.WireframeGeometry(geometry);
        this.wireframeMaterial = new THREE.LineBasicMaterial({
            color: 0x00ffcc,
            transparent: true,
            opacity: 0.15,
        });
        this.wireframe = new THREE.LineSegments(wireGeom, this.wireframeMaterial);

        // Posicionar
        this.head.position.y = 0;
        this.wireframe.position.y = 0;

        scene.add(this.head);
        scene.add(this.wireframe);

        return this;
    },

    update(time) {
        if (this.material) {
            this.material.uniforms.uTime.value = time;
        }
        // Leve rotación automática
        if (this.head) {
            this.head.rotation.y += 0.002;
            this.wireframe.rotation.y += 0.002;
        }
    }
};