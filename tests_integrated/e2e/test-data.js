/**
 * E2E 테스트를 위한 테스트 데이터 설정
 * 
 * 이 스크립트는 Django 관리 명령어를 통해 테스트 데이터를 생성합니다.
 */

const { execSync } = require('child_process');
const path = require('path');

/**
 * 테스트 데이터 생성
 */
function createTestData() {
  try {
    console.log('테스트 데이터 생성 중...');
    
    // Django 관리 명령어 실행
    const projectRoot = path.resolve(__dirname, '../..');
    const command = 'python manage.py create_test_data';
    
    execSync(command, {
      cwd: projectRoot,
      stdio: 'inherit',
    });
    
    console.log('테스트 데이터 생성 완료');
    return true;
  } catch (error) {
    console.error('테스트 데이터 생성 실패:', error);
    return false;
  }
}

/**
 * 테스트 데이터 정리
 */
function cleanupTestData() {
  try {
    console.log('테스트 데이터 정리 중...');
    
    // Django 관리 명령어 실행
    const projectRoot = path.resolve(__dirname, '../..');
    const command = 'python manage.py cleanup_test_data';
    
    execSync(command, {
      cwd: projectRoot,
      stdio: 'inherit',
    });
    
    console.log('테스트 데이터 정리 완료');
    return true;
  } catch (error) {
    console.error('테스트 데이터 정리 실패:', error);
    return false;
  }
}

module.exports = {
  createTestData,
  cleanupTestData,
};