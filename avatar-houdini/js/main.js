/**
 * main.js — Orquestador minimal Paso 1
 */
(function() {
    const container = document.getElementById('scene-container');
    const loading = document.getElementById('loading');

    // ─── Escena ───
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050510);

    // ─── Cámara ───
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0.05, 1.3);
    camera.lookAt(0, 0, 0);

    // ─── Renderer ───
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x050510, 1);
    container.appendChild(renderer.domElement);

    // ─── Resize ───
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // ─── Crear rostro ───
    const face = Object.create(HoudiniFace);
    face.create(scene);

    // Ocultar loading
    loading.style.display = 'none';

    // ─── Mouse tracking ───
    let mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
        mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    });
    document.addEventListener('touchmove', (e) => {
        if (e.touches.length > 0) {
            mouseX = (e.touches[0].clientX / window.innerWidth - 0.5) * 2;
            mouseY = (e.touches[0].clientY / window.innerHeight - 0.5) * 2;
        }
    });

    // ─── Loop ───
    let clock = new THREE.Clock();

    function animate() {
        requestAnimationFrame(animate);

        const time = clock.getElapsedTime();

        // Actualizar rostro
        face.update(time);

        // Rotación sutil con mouse
        if (face.head) {
            const targetRotY = mouseX * 0.3;
            const targetRotX = mouseY * 0.15;
            face.head.rotation.x += (targetRotX - face.head.rotation.x) * 0.02;
            face.head.rotation.y += (targetRotY - face.head.rotation.y) * 0.02;
            face.wireframe.rotation.x = face.head.rotation.x;
            face.wireframe.rotation.y = face.head.rotation.y;
        }

        renderer.render(scene, camera);
    }

    animate();
})();